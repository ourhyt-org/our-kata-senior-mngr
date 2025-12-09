import os
import json
from typing import Dict, Any

import boto3
import jwt
from datetime import datetime, timedelta, timezone

JWT_SECRET_CACHE: dict[str, str] = {}

def _get_jwt_secret() -> str:
    if "value" in JWT_SECRET_CACHE:
        return JWT_SECRET_CACHE["value"]

    direct = os.getenv("JWT_SECRET_VALUE")
    if direct:
        JWT_SECRET_CACHE["value"] = direct
        return direct

    secret_name = os.getenv("JWT_SECRET_NAME")
    if not secret_name:
        raise RuntimeError("JWT_SECRET_NAME o JWT_SECRET_VALUE no configurados")

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    secret_string = response.get("SecretString")

    if not secret_string:
        raise RuntimeError("SecretString vacío en Secrets Manager para JWT")

    try:
        data = json.loads(secret_string)
        secret_value = data.get("JWT_SECRET")
    except json.JSONDecodeError:
        secret_value = secret_string

    if not secret_value:
        raise RuntimeError("No se encontró JWT_SECRET en el secreto")

    JWT_SECRET_CACHE["value"] = secret_value
    return secret_value


def create_auth_token(
    claims: Dict[str, Any],
    expires_in_seconds: int = 600,
) -> str:
    secret = _get_jwt_secret()
    now = datetime.now(tz=timezone.utc)
    payload = {
        **claims,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
    }

    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


def verify_auth_token(token: str) -> Dict[str, Any]:
    secret = _get_jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expirado")
    except jwt.InvalidTokenError:
        raise ValueError("Token inválido")