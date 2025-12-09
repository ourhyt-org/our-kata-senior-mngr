
import uuid
import random
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.utils.token_utils import create_auth_token
from app.services.customer_repo import get_customer_by_document

router = APIRouter()

MAX_ALLOWED_RISK = 0.8
CHALLENGES = ("BLINK", "APPROACH")


class StartRequest(BaseModel):
    docType: str = Field(..., description="Tipo de documento, ej: CC")
    docNumber: str = Field(..., description="Número de documento")
    phone: str = Field(..., description="Teléfono celular")


class StartResponse(BaseModel):
    authId: str
    token: str
    nextStep: str
    customerStatus: str
    riskScore: float
    reason: Optional[str]
    name: str
    allowedProducts: list[str]
    challengeType: str


@router.post("/start", response_model=StartResponse)
def start_auth(request: StartRequest):
    customer = get_customer_by_document(request.docType, request.docNumber)

    if customer is None:
        raise HTTPException(
            status_code=403,
            detail="Documento no registrado en la base de clientes",
        )

    blocked = bool(customer.get("blocked", False))
    risk_score = float(customer.get("riskScore", 0.0))
    status = customer.get("status", "UNKNOWN")
    reason = customer.get("reason")

    if blocked or risk_score > MAX_ALLOWED_RISK:
        auth_id = str(uuid.uuid4())
        print(
            f"[START] REJECTED authId={auth_id} doc={request.docType}-{request.docNumber} "
            f"blocked={blocked} risk={risk_score}"
        )
        return StartResponse(
            authId=auth_id,
            token="",
            nextStep="REJECTED",
            customerStatus=status,
            riskScore=risk_score,
            reason=reason or "Cliente bloqueado o con riesgo alto",
            name=customer.get("name", ""),
            allowedProducts=customer.get("allowedProducts", []),
            challengeType="NONE",
        )

    auth_id = str(uuid.uuid4())
    challenge_type = random.choice(CHALLENGES)

    claims = {
        "sub": "auth-session",
        "auth_id": auth_id,
        "doc_type": request.docType,
        "doc_number": request.docNumber,
        "phone": request.phone,
        "challenge_type": challenge_type,
    }

    token = create_auth_token(claims)

    print(
        f"[START] OK authId={auth_id} doc={request.docType}-{request.docNumber} "
        f"risk={risk_score} challenge={challenge_type}"
    )

    return StartResponse(
        authId=auth_id,
        token=token,
        nextStep="DOCUMENT",
        customerStatus=status,
        riskScore=risk_score,
        reason=reason,
        name=customer.get("name", ""),
        allowedProducts=customer.get("allowedProducts", []),
        challengeType=challenge_type,
    )