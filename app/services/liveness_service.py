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
    face_match: Optional[bool] = None
    face_similarity: Optional[float] = None


LIVENESS_FRAMES_BUCKET = os.getenv("LIVENESS_FRAMES_BUCKET", "ourhyt-assets")
LIVENESS_ENGINE_NAME = os.getenv(
    "LIVENESS_ENGINE_NAME",
    "ourhyt-kata-liveness-engine-dev"
)


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
    doc_number: str,
) -> dict:
    payload = {
        "authId": auth_id,
        "challengeType": challenge_type,
        "bucket": bucket,
        "frameKeys": frame_keys,
        "docNumber": doc_number,
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
        doc_number=doc_number,
    )

    liveness_score = float(engine_result.get("livenessScore", 0.0))
    engine_passed = bool(engine_result.get("passed", False))
    reason = engine_result.get("reason")

    face_match = engine_result.get("faceMatch")
    face_similarity = engine_result.get("faceSimilarity")
    face_match_info = engine_result.get("faceMatchInfo") or {}

    if not engine_passed:
        passed = False
        next_step = "REJECTED"
    else:
        if face_match is True:
            passed = True
            next_step = "COMPLETED"
        elif face_match is False:
            passed = False
            next_step = "REJECTED"
            extra = "El rostro no coincide con el documento presentado."
            if reason:
                reason = f"{reason} Además, {extra}"
            else:
                reason = extra
        else:
            error = face_match_info.get("error")
            passed = False
            next_step = "REJECTED"

            if error:
                print(f"[LIVENESS] Rekognition error: {error}")
                extra = "No se pudo verificar coincidencia de rostro con el documento."
            else:
                extra = "No se pudo determinar si el rostro coincide con el documento."

            if reason:
                reason = f"{reason} {extra}"
            else:
                reason = extra

    return LivenessResult(
        auth_id=auth_id,
        challenge_type=challenge_type,
        liveness_score=liveness_score,
        passed=passed,
        reason=reason,
        next_step=next_step,
        face_match=face_match,
        face_similarity=float(face_similarity) if face_similarity is not None else None,
    )