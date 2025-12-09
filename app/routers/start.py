# app/routers/start.py
import os
import uuid
import random
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.utils.token_utils import create_auth_token

router = APIRouter()

MOCK_CUSTOMERS_URL = os.getenv(
    "MOCK_CUSTOMERS_URL",
    "https://demo1097960.mockable.io/customers",
)

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
    try:
        print(f"🔍 Searching customer in mock: {MOCK_CUSTOMERS_URL}")
        resp = requests.get(MOCK_CUSTOMERS_URL, timeout=3)
        resp.raise_for_status()
        customers = resp.json()
        print(f"✅ Mock returned {len(customers)} customers")
    except Exception as e:
        print(f"❌ Error calling mock: {e}")
        raise HTTPException(status_code=502, detail="No se pudo consultar la base de clientes mock")

    customer = next(
        (
            c for c in customers
            if c.get("docType") == request.docType
            and str(c.get("docNumber")) == str(request.docNumber)
        ),
        None,
    )

    if not customer:
        raise HTTPException(status_code=403, detail="Documento no registrado en la base de clientes")

    blocked = bool(customer.get("blocked", False))
    risk_score = float(customer.get("riskScore", 0.0))
    status = customer.get("status", "UNKNOWN")
    reason = customer.get("reason")

    if blocked or risk_score > MAX_ALLOWED_RISK:
        return StartResponse(
            authId=str(uuid.uuid4()),
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
        f"[START] authId={auth_id} doc={request.docType}-{request.docNumber} "
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