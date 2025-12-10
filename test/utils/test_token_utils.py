
import pytest
import os
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

import jwt

os.environ["JWT_SECRET_SECRET_NAME"] = "test-secret-key-for-jwt-testing"

from app.utils.token_utils import (
    create_auth_token,
    verify_auth_token,
    _get_jwt_secret,
    JWT_SECRET_CACHE,
)


class TestGetJwtSecret:
    
    def setup_method(self):
        JWT_SECRET_CACHE.clear()
    
    def test_get_jwt_secret_from_direct_env(self):
        os.environ["JWT_SECRET_SECRET_NAME"] = "my-direct-secret"
        JWT_SECRET_CACHE.clear()
        
        secret = _get_jwt_secret()
        
        assert secret == "my-direct-secret"
        assert JWT_SECRET_CACHE["value"] == "my-direct-secret"
    
    def test_get_jwt_secret_from_cache(self):
        JWT_SECRET_CACHE["value"] = "cached-secret"
        
        secret = _get_jwt_secret()
        
        assert secret == "cached-secret"
    
    @patch.dict(os.environ, {"JWT_SECRET_SECRET_NAME": "", "JWT_SECRET_NAME": "my-secret-name"}, clear=False)
    @patch("boto3.client")
    def test_get_jwt_secret_from_secrets_manager(self, mock_boto_client):
        JWT_SECRET_CACHE.clear()
        os.environ.pop("JWT_SECRET_SECRET_NAME", None)
        os.environ["JWT_SECRET_NAME"] = "my-secret-name"
        
        mock_secrets_client = MagicMock()
        mock_secrets_client.get_secret_value.return_value = {
            "SecretString": json.dumps({"JWT_SECRET": "secret-from-aws"})
        }
        mock_boto_client.return_value = mock_secrets_client
        
        secret = _get_jwt_secret()
        
        assert secret == "secret-from-aws"
        mock_secrets_client.get_secret_value.assert_called_once_with(SecretId="my-secret-name")
    
    @patch.dict(os.environ, {"JWT_SECRET_SECRET_NAME": "", "JWT_SECRET_NAME": "my-secret-name"}, clear=False)
    @patch("boto3.client")
    def test_get_jwt_secret_plain_string_from_secrets_manager(self, mock_boto_client):
        JWT_SECRET_CACHE.clear()
        os.environ.pop("JWT_SECRET_SECRET_NAME", None)
        os.environ["JWT_SECRET_NAME"] = "my-secret-name"
        
        mock_secrets_client = MagicMock()
        mock_secrets_client.get_secret_value.return_value = {
            "SecretString": "plain-secret-value"
        }
        mock_boto_client.return_value = mock_secrets_client
        
        secret = _get_jwt_secret()
        
        assert secret == "plain-secret-value"


class TestCreateAuthToken:
    
    def setup_method(self):
        JWT_SECRET_CACHE.clear()
        os.environ["JWT_SECRET_SECRET_NAME"] = "test-secret"
    
    def test_create_auth_token_basic(self, sample_jwt_claims):
        token = create_auth_token(sample_jwt_claims)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert decoded["auth_id"] == sample_jwt_claims["auth_id"]
        assert decoded["doc_number"] == sample_jwt_claims["doc_number"]
    
    def test_create_auth_token_includes_iat_and_exp(self, sample_jwt_claims):
        token = create_auth_token(sample_jwt_claims, expires_in_seconds=600)
        
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])
        
        assert "iat" in decoded
        assert "exp" in decoded
        assert decoded["exp"] > decoded["iat"]
        assert decoded["exp"] - decoded["iat"] == 600
    
    def test_create_auth_token_custom_expiration(self, sample_jwt_claims):
        token = create_auth_token(sample_jwt_claims, expires_in_seconds=1800)
        
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])
        
        assert decoded["exp"] - decoded["iat"] == 1800


class TestVerifyAuthToken:

    def setup_method(self):
        JWT_SECRET_CACHE.clear()
        os.environ["JWT_SECRET_SECRET_NAME"] = "test-secret"
    
    def test_verify_auth_token_valid(self, sample_jwt_claims):
        token = create_auth_token(sample_jwt_claims)
        
        payload = verify_auth_token(token)
        
        assert payload["auth_id"] == sample_jwt_claims["auth_id"]
        assert payload["doc_number"] == sample_jwt_claims["doc_number"]
        assert payload["challenge_type"] == sample_jwt_claims["challenge_type"]
    
    def test_verify_auth_token_expired(self, sample_jwt_claims):
        secret = "test-secret"
        now = datetime.now(tz=timezone.utc)
        payload = {
            **sample_jwt_claims,
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
        }
        expired_token = jwt.encode(payload, secret, algorithm="HS256")
        
        with pytest.raises(ValueError) as exc_info:
            verify_auth_token(expired_token)
        
        assert "Token expirado" in str(exc_info.value)
    
    def test_verify_auth_token_invalid_signature(self, sample_jwt_claims):
        wrong_secret = "wrong-secret"
        now = datetime.now(tz=timezone.utc)
        payload = {
            **sample_jwt_claims,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        }
        invalid_token = jwt.encode(payload, wrong_secret, algorithm="HS256")
        
        with pytest.raises(ValueError) as exc_info:
            verify_auth_token(invalid_token)
        
        assert "Token inválido" in str(exc_info.value)
    
    def test_verify_auth_token_malformed(self):
        with pytest.raises(ValueError) as exc_info:
            verify_auth_token("not-a-valid-jwt-token")
        
        assert "Token inválido" in str(exc_info.value)
    
    def test_verify_auth_token_empty(self):
        with pytest.raises(ValueError) as exc_info:
            verify_auth_token("")
        
        assert "Token inválido" in str(exc_info.value)

