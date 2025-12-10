from fastapi import APIRouter, UploadFile, File, Header, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.utils.token_utils import verify_auth_token
from app.services.document_service import evaluate_document

router = APIRouter()


class DocumentResponse(BaseModel):
    authId: str
    qualityScore: float
    documentStatus: str
    reason: Optional[str]
    nextStep: str
    ocrDocNumber: Optional[str]
    docMatch: bool
    fraudSuspected: bool


@router.post("/document", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ", 1)[1].strip()

    try:
        claims = verify_auth_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    auth_id = claims.get("auth_id")
    jwt_doc_number = claims.get("doc_number")

    if not auth_id or not jwt_doc_number:
        raise HTTPException(status_code=400, detail="Token inválido o incompleto")

    print(f"[DOCUMENT] IN authId={auth_id[:8]}... doc={jwt_doc_number[:4]}***")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    
    try:
        result = evaluate_document(
            auth_id=auth_id,
            jwt_doc_number=jwt_doc_number,
            image_bytes=contents,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    print(
        f"[DOCUMENT] OUT authId={result.auth_id[:8]}... "
        f"status={result.document_status} match={result.doc_match} fraud={result.fraud_suspected}"
    )

    return DocumentResponse(
        authId=result.auth_id,
        qualityScore=result.quality_score,
        documentStatus=result.document_status,
        reason=result.reason,
        nextStep=result.next_step,
        ocrDocNumber=result.ocr_doc_number,
        docMatch=result.doc_match,
        fraudSuspected=result.fraud_suspected,
    )
