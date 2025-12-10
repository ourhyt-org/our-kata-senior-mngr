from fastapi import APIRouter, UploadFile, File, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from app.utils.token_utils import verify_auth_token
from app.services.liveness_service import evaluate_liveness

router = APIRouter()


class LivenessResponse(BaseModel):
    authId: str
    challengeType: str
    livenessScore: float
    passed: bool
    reason: Optional[str] = None
    nextStep: str

@router.post("/liveness", response_model=LivenessResponse)
async def liveness_check(
    frames: List[UploadFile] = File(...),
    authorization: Optional[str] = Header(None),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header"
        )

    token = authorization.split(" ", 1)[1].strip()

    try:
        claims = verify_auth_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    auth_id = claims.get("auth_id")
    challenge_type = claims.get("challenge_type")
    doc_number = claims.get("doc_number")

    if not auth_id:
        raise HTTPException(status_code=400, detail="Token inválido o sin authId")
    if not challenge_type:
        raise HTTPException(status_code=400, detail="Token sin challengeType")

    print(f"[LIVENESS] IN authId={auth_id[:8]}... frames={len(frames)} challenge={challenge_type}")

    if not frames or len(frames) < 2:
        raise HTTPException(
            status_code=400,
            detail="Se requieren al menos 2 frames"
        )

    frame_bytes_list: List[bytes] = []
    for f in frames:
        content = await f.read()
        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uno de los frames viene vacío"
            )
        frame_bytes_list.append(content)

    try:
        result = evaluate_liveness(
            auth_id=auth_id,
            challenge_type=challenge_type,
            doc_number=doc_number,
            frames_bytes=frame_bytes_list,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    print(
        f"[LIVENESS] OUT authId={result.auth_id[:8]}... "
        f"passed={result.passed} score={result.liveness_score:.2f} faceMatch={result.face_match}"
    )

    return LivenessResponse(
        authId=result.auth_id,
        challengeType=result.challenge_type,
        livenessScore=result.liveness_score,
        passed=result.passed,
        reason=result.reason,
        nextStep=result.next_step,
    )
