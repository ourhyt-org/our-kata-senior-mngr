
import pytest
import os
from unittest.mock import patch, MagicMock
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

os.environ["JWT_SECRET_SECRET_NAME"] = "test-secret-key-for-jwt-testing"

from app.main import app
from app.utils.token_utils import create_auth_token, JWT_SECRET_CACHE
from app.services.document_service import DocumentEvaluationResult

client = TestClient(app)


def create_test_image():
    img = Image.new("RGB", (800, 600), color="white")
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer


def get_valid_token():
    JWT_SECRET_CACHE.clear()
    os.environ["JWT_SECRET_SECRET_NAME"] = "test-secret-key-for-jwt-testing"
    return create_auth_token({
        "sub": "auth-session",
        "auth_id": "test-auth-123",
        "doc_type": "CC",
        "doc_number": "12345678",
        "phone": "3001234567",
        "challenge_type": "BLINK",
    })


class TestDocumentEndpoint:
    
    @patch("app.routers.document.evaluate_document")
    def test_upload_document_success(self, mock_evaluate):
        mock_evaluate.return_value = DocumentEvaluationResult(
            auth_id="test-auth-123",
            quality_score=0.9,
            document_status="OK",
            reason=None,
            next_step="LIVENESS",
            ocr_doc_number="12345678",
            doc_match=True,
            fraud_suspected=False,
        )
        
        token = get_valid_token()
        image = create_test_image()
        
        response = client.post(
            "/kata/auth/document",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("document.jpg", image, "image/jpeg")},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["authId"] == "test-auth-123"
        assert data["documentStatus"] == "OK"
        assert data["nextStep"] == "LIVENESS"
        assert data["docMatch"] is True
    
    def test_upload_document_missing_auth(self):
        image = create_test_image()
        
        response = client.post(
            "/kata/auth/document",
            files={"file": ("document.jpg", image, "image/jpeg")},
        )
        
        assert response.status_code == 401
        assert "Authorization" in response.json()["detail"]
    
    def test_upload_document_invalid_auth_format(self):
        image = create_test_image()
        
        response = client.post(
            "/kata/auth/document",
            headers={"Authorization": "Basic sometoken"},
            files={"file": ("document.jpg", image, "image/jpeg")},
        )
        
        assert response.status_code == 401
    
    def test_upload_document_invalid_token(self):
        image = create_test_image()
        
        response = client.post(
            "/kata/auth/document",
            headers={"Authorization": "Bearer invalid-token"},
            files={"file": ("document.jpg", image, "image/jpeg")},
        )
        
        assert response.status_code == 401
    
    @patch("app.routers.document.verify_auth_token")
    def test_upload_document_token_missing_auth_id(self, mock_verify):
        mock_verify.return_value = {
            "doc_number": "12345678",
        }
        
        image = create_test_image()
        
        response = client.post(
            "/kata/auth/document",
            headers={"Authorization": "Bearer some-token"},
            files={"file": ("document.jpg", image, "image/jpeg")},
        )
        
        assert response.status_code == 400
        assert "inválido" in response.json()["detail"]
    
    @patch("app.routers.document.verify_auth_token")
    def test_upload_document_token_missing_doc_number(self, mock_verify):
        mock_verify.return_value = {
            "auth_id": "test-auth-123",
        }
        
        image = create_test_image()
        
        response = client.post(
            "/kata/auth/document",
            headers={"Authorization": "Bearer some-token"},
            files={"file": ("document.jpg", image, "image/jpeg")},
        )
        
        assert response.status_code == 400
        assert "inválido" in response.json()["detail"]
    
    @patch("app.routers.document.evaluate_document")
    def test_upload_document_empty_file(self, mock_evaluate):
        token = get_valid_token()
        
        response = client.post(
            "/kata/auth/document",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("document.jpg", BytesIO(b""), "image/jpeg")},
        )
        
        assert response.status_code == 400
        assert "vacío" in response.json()["detail"]
    
    @patch("app.routers.document.evaluate_document")
    def test_upload_document_fraud_detected(self, mock_evaluate):
        mock_evaluate.return_value = DocumentEvaluationResult(
            auth_id="test-auth-123",
            quality_score=0.8,
            document_status="MISMATCH",
            reason="Número de documento no coincide",
            next_step="REJECTED",
            ocr_doc_number="87654321",
            doc_match=False,
            fraud_suspected=True,
        )
        
        token = get_valid_token()
        image = create_test_image()
        
        response = client.post(
            "/kata/auth/document",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("document.jpg", image, "image/jpeg")},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["fraudSuspected"] is True
        assert data["docMatch"] is False
        assert data["nextStep"] == "REJECTED"
    
    @patch("app.routers.document.evaluate_document")
    def test_upload_document_low_quality(self, mock_evaluate):
        mock_evaluate.return_value = DocumentEvaluationResult(
            auth_id="test-auth-123",
            quality_score=0.4,
            document_status="RETAKE",
            reason="Resolución muy baja",
            next_step="RETAKE_DOCUMENT",
            ocr_doc_number=None,
            doc_match=False,
            fraud_suspected=False,
        )
        
        token = get_valid_token()
        image = create_test_image()
        
        response = client.post(
            "/kata/auth/document",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("document.jpg", image, "image/jpeg")},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["documentStatus"] == "RETAKE"
        assert data["nextStep"] == "RETAKE_DOCUMENT"
    
    @patch("app.routers.document.evaluate_document")
    def test_upload_document_invalid_image(self, mock_evaluate):    
        mock_evaluate.side_effect = ValueError("El archivo no es una imagen válida")
        
        token = get_valid_token()
        
        response = client.post(
            "/kata/auth/document",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("document.txt", BytesIO(b"not an image"), "text/plain")},
        )
        
        assert response.status_code == 400
        assert "imagen válida" in response.json()["detail"]

