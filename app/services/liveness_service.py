
from dataclasses import dataclass
from typing import Optional, List
import os
import json

import boto3

s3_client = boto3.client("s3")
lambda_client = boto3.client("lambda")


@dataclass
class LivenessResult:
    auth_id: str
    challenge_type: str
    liveness_score: float
    passed: bool
    reason: Optional[str]
    next_step: str


LIVENESS_FRAMES_BUCKET = os.getenv("LIVENESS_FRAMES_BUCKET", "ourhyt-assets")
LIVENESS_ENGINE_NAME = os.getenv("LIVENESS_ENGINE_NAME", "ourhyt-kata-liveness-engine-dev")


def _upload_frame_to_s3(
    bucket: str,
    key: str,
    content: bytes,
    content_type: str = "image/jpeg",
) -> None:
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=content,
        ContentType=content_type,
    )


def _invoke_liveness_engine(
    auth_id: str,
    challenge_type: str,
    bucket: str,
    frame_keys: List[str],
) -> dict:
    payload = {
        "authId": auth_id,
        "challengeType": challenge_type,
        "bucket": bucket,
        "frameKeys": frame_keys,
    }

    response = lambda_client.invoke(
        FunctionName=LIVENESS_ENGINE_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )

    raw_body = response["Payload"].read().decode("utf-8")

    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        raise ValueError(f"Respuesta inválida del liveness-engine: {raw_body}")

    if isinstance(body, dict) and "statusCode" in body:
        engine_payload = json.loads(body.get("body", "{}"))
    else:
        engine_payload = body

    return engine_payload


def evaluate_liveness(
    auth_id: str,
    challenge_type: str,
    doc_number: str,
    frames_bytes: List[bytes],
) -> LivenessResult:
    if not doc_number:
        doc_number = "unknown-doc"

    if not frames_bytes or len(frames_bytes) < 2:
        raise ValueError("Se requieren al menos 2 frames para liveness")

    base_prefix = f"liveness/{doc_number}/{auth_id}"

    frame_keys: List[str] = []

    for idx, content in enumerate(frames_bytes, start=1):
        key = f"{base_prefix}/frame_{idx:03d}.jpg"
        _upload_frame_to_s3(LIVENESS_FRAMES_BUCKET, key, content)
        frame_keys.append(key)

    engine_result = _invoke_liveness_engine(
        auth_id=auth_id,
        challenge_type=challenge_type,
        bucket=LIVENESS_FRAMES_BUCKET,
        frame_keys=frame_keys,
    )

    liveness_score = float(engine_result.get("livenessScore", 0.0))
    passed = bool(engine_result.get("passed", False))
    reason = engine_result.get("reason")

    next_step = "COMPLETED" if passed else "REJECTED"

    return LivenessResult(
        auth_id=auth_id,
        challenge_type=challenge_type,
        liveness_score=liveness_score,
        passed=passed,
        reason=reason,
        next_step=next_step,
    )