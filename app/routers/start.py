from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import uuid

from app.utils.token_utils import generate_auth_token
from app.services.customer_repo import get_customer_by_document

router = APIRouter()


class StartRequest(BaseModel):
    docType: str = Field(..., example="CC")
    docNumber: str = Field(..., example="1088330322")
    phone: str = Field(..., example="3001234567")


class StartResponse(BaseModel):
    authId: str
    token: str | None
    nextStep: str
    customerStatus: str
    riskScore: float
    reason: str | None = None
    name: str | None = None
    allowedProducts: list[str] = []


@router.post("/start", response_model=StartResponse)
def start_auth(data: StartRequest):
    customer = get_customer_by_document(data.docType, data.docNumber)

    if not customer:
        raise HTTPException(
            status_code=403,
            detail="Documento no registrado en la base de clientes",
        )

    blocked = bool(customer.get("blocked", False))
    risk_score = float(customer.get("riskScore", 0.0))
    status = customer.get("status", "UNKNOWN")
    reason = customer.get("reason")
    name = customer.get("name")
    allowed_products = customer.get("allowedProducts", [])

    auth_id = str(uuid.uuid4())

    if blocked or status == "BLOCKED":
        return StartResponse(
            authId=auth_id,
            token=None,
            nextStep="REJECTED",
            customerStatus=status,
            riskScore=risk_score,
            reason=reason or "Cliente bloqueado por riesgo o suplantación",
            name=name,
            allowedProducts=allowed_products,
        )

    token = generate_auth_token(
        auth_id=auth_id,
        doc_type=data.docType,
        doc_number=data.docNumber,
        phone=data.phone,
        ttl_seconds=600,
    )

    return StartResponse(
        authId=auth_id,
        token=token,
        nextStep="DOCUMENT",
        customerStatus=status,
        riskScore=risk_score,
        reason=reason,
        name=name,
        allowedProducts=allowed_products,
    )