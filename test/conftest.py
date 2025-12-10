
import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from io import BytesIO

from PIL import Image
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["JWT_SECRET_SECRET_NAME"] = "test-secret-key-for-jwt-testing"
os.environ["CUSTOMERS_API_URL"] = "https://mock-api.test/customers"
os.environ["LIVENESS_FRAMES_BUCKET"] = "test-bucket"
os.environ["LIVENESS_ENGINE_NAME"] = "test-liveness-engine"


@pytest.fixture
def jwt_secret():
    return "test-secret-key-for-jwt-testing"


@pytest.fixture
def sample_customer():
    return {
        "docType": "CC",
        "docNumber": "12345678",
        "name": "Juan Pérez",
        "phone": "3001234567",
        "status": "ACTIVE",
        "blocked": False,
        "riskScore": 0.2,
        "reason": None,
        "allowedProducts": ["CREDIT", "SAVINGS"],
    }


@pytest.fixture
def blocked_customer():
    return {
        "docType": "CC",
        "docNumber": "87654321",
        "name": "Cliente Bloqueado",
        "phone": "3009876543",
        "status": "BLOCKED",
        "blocked": True,
        "riskScore": 0.9,
        "reason": "Fraude detectado",
        "allowedProducts": [],
    }


@pytest.fixture
def high_risk_customer():
    return {
        "docType": "CC",
        "docNumber": "11111111",
        "name": "Cliente Riesgoso",
        "phone": "3001111111",
        "status": "REVIEW",
        "blocked": False,
        "riskScore": 0.95,
        "reason": "Score de riesgo elevado",
        "allowedProducts": [],
    }


@pytest.fixture
def valid_image_bytes():
    img = Image.new("RGB", (800, 600), color="white")
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def small_image_bytes():
    img = Image.new("RGB", (200, 150), color="white")
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def dark_image_bytes():
    img = Image.new("RGB", (800, 600), color="black")
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def bright_image_bytes():
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def invalid_image_bytes():
    return b"estos no son bytes de imagen valida"


@pytest.fixture
def mock_boto3_clients():
    with patch("boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_lambda = MagicMock()
        mock_textract = MagicMock()
        mock_secrets = MagicMock()
        
        def client_factory(service_name, **kwargs):
            if service_name == "s3":
                return mock_s3
            elif service_name == "lambda":
                return mock_lambda
            elif service_name == "textract":
                return mock_textract
            elif service_name == "secretsmanager":
                return mock_secrets
            return MagicMock()
        
        mock_client.side_effect = client_factory
        yield {
            "s3": mock_s3,
            "lambda": mock_lambda,
            "textract": mock_textract,
            "secretsmanager": mock_secrets,
        }


@pytest.fixture
def sample_jwt_claims():
    return {
        "sub": "auth-session",
        "auth_id": "test-auth-id-123",
        "doc_type": "CC",
        "doc_number": "12345678",
        "phone": "3001234567",
        "challenge_type": "BLINK",
    }


@pytest.fixture
def test_client():
    from app.main import app
    return TestClient(app)


@pytest.fixture
def mock_textract_response():
    return {
        "Blocks": [
            {"BlockType": "LINE", "Text": "REPÚBLICA DE COLOMBIA"},
            {"BlockType": "LINE", "Text": "CÉDULA DE CIUDADANÍA"},
            {"BlockType": "LINE", "Text": "12345678"},
            {"BlockType": "LINE", "Text": "JUAN PÉREZ GARCÍA"},
        ]
    }


@pytest.fixture
def mock_liveness_engine_response():
    return {
        "statusCode": 200,
        "body": '{"livenessScore": 0.95, "passed": true, "reason": null}'
    }


@pytest.fixture
def mock_liveness_engine_failed_response(): 
    return {
        "statusCode": 200,
        "body": '{"livenessScore": 0.3, "passed": false, "reason": "No se detectó movimiento"}'
    }

