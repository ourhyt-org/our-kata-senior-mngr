from fastapi import APIRouter, Header, HTTPException
from app.utils.token_utils import verify_auth_token

router = APIRouter()

@router.post("/liveness")
def liveness_check(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")

    token = authorization.replace("Bearer ", "")

    try:
        claims = verify_auth_token(token)
    except Exception as e:
        raise HTTPException(401, str(e))

    return {
        "authId": claims["auth_id"],
        "liveness": "PASSED",
        "nextStep": "COMPLETED"
    }