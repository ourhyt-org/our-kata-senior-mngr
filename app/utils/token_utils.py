import os
import time
import json

import jwt
from jwt import InvalidTokenError
import boto3

JWT_ALG = "HS256"

_cached_jwt_secret = None


def _load_jwt_secret() -> str:
    global _cached_jwt_secret

    if _cached_jwt_secret:
        return _cached_jwt_secret

    secret_name = os.environ.get("JWT_SECRET_SECRET_NAME")
    if secret_name:
        region = os.environ.get("AWS_REGION", "us-east-1")
        client = boto3.client("secretsmanager", region_name=region)

        resp = client.get_secret_value(SecretId=secret_name)
        secret_string = resp.get("SecretString", "")

        try:
            data = json.loads(secret_string)
            secret_value = data.get("JWT_SECRET")
        except json.JSONDecodeError:
            secret_value = secret_string

        if not secret_value:
            raise RuntimeError("JWT_SECRET no encontrado dentro del secreto de Secrets Manager")

        _cached_jwt_secret = secret_value
        return _cached_jwt_secret

    env_secret = os.environ.get("JWT_SECRET")
    if not env_secret:
        raise RuntimeError("No JWT secret configured (ni Secrets Manager ni env var)")

    _cached_jwt_secret = env_secret
    return _cached_jwt_secret


def generate_auth_token(auth_id, doc_type, doc_number, phone, ttl_seconds=600):
    now = int(time.time())
    payload = {
        "sub": "auth-session",
        "auth_id": auth_id,
        "doc_type": doc_type,
        "doc_number": doc_number,
        "phone": phone,
        "iat": now,
        "exp": now + ttl_seconds,
    }

    secret = _load_jwt_secret()
    return jwt.encode(payload, secret, algorithm=JWT_ALG)


def verify_auth_token(token: str):
    secret = _load_jwt_secret()
    try:
        return jwt.decode(token, secret, algorithms=[JWT_ALG])
    except InvalidTokenError as e:
        raise ValueError("Invalid token: " + str(e))