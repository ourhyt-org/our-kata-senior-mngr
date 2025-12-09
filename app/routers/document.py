from fastapi import APIRouter, UploadFile, File, Header, HTTPException
from app.utils.token_utils import verify_auth_token
from app.utils.image_utils import evaluate_image_quality
from app.services.ocr_service import extract_text_from_image

router = APIRouter()

@router.post("/document")
async def process_document(
    file: UploadFile = File(...),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")

    token = authorization.replace("Bearer ", "")

    try:
        claims = verify_auth_token(token)
    except Exception as e:
        raise HTTPException(401, str(e))

    image_bytes = await file.read()

    quality_score = evaluate_image_quality(image_bytes)
    if quality_score < 0.5:
        raise HTTPException(400, "Image quality too low, please retake")

    extracted_text = extract_text_from_image(image_bytes)

    return {
        "authId": claims["auth_id"],
        "qualityScore": quality_score,
        "textExtracted": extracted_text,
        "nextStep": "LIVENESS"
    }