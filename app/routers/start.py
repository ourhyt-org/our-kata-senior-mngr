from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid
from app.utils.token_utils import generate_auth_token

router = APIRouter()

class StartRequest(BaseModel):
    docType: str
    docNumber: str
    phone: str

@router.post("/start")
def start_auth(data: StartRequest):
    # Crear ID único de sesión
    auth_id = str(uuid.uuid4())

    # Generar token firmado
    token = generate_auth_token(
        auth_id=auth_id,
        doc_type=data.docType,
        doc_number=data.docNumber,
        phone=data.phone
    )

    return {
        "authId": auth_id,
        "token": token,
        "nextStep": "DOCUMENT"
    }