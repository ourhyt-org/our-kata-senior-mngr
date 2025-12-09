import os
import time
import jwt
from jwt import InvalidTokenError

JWT_SECRET = os.environ.get("JWT_SECRET", "DEV_SECRET")
JWT_ALG = "HS256"

def generate_auth_token(auth_id, doc_type, doc_number, phone, ttl_seconds=600):
    now = int(time.time())
    payload = {
        "sub": "auth-session",
        "auth_id": auth_id,
        "doc_type": doc_type,
        "doc_number": doc_number,
        "phone": phone,
        "iat": now,
        "exp": now + ttl_seconds
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def verify_auth_token(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except InvalidTokenError as e:
        raise ValueError("Invalid token: " + str(e))