
import os
from unittest.mock import patch, MagicMock
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

os.environ["JWT_SECRET_SECRET_NAME"] = "test-secret-key-for-jwt-testing"

from app.main import app
from app.utils.token_utils import create_auth_token, JWT_SECRET_CACHE
from app.services.liveness_service import LivenessResult

client = TestClient(app)


def create_test_frame():
    img = Image.new("RGB", (640, 480), color="white")
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


class TestLivenessEndpoint:
    
    @patch("app.routers.liveness.evaluate_liveness")
    def test_liveness_check_success(self, mock_evaluate):
        mock_evaluate.return_value = LivenessResult(
            auth_id="test-auth-123",
            challenge_type="BLINK",
            liveness_score=0.95,
            passed=True,
            reason=None,
            next_step="COMPLETED",
        )
        
        token = get_valid_token()
        frame1 = create_test_frame()
        frame2 = create_test_frame()
        
        response = client.post(
            "/kata/auth/liveness",
            headers={"Authorization": f"Bearer {token}"},
            files=[
                ("frames", ("frame1.jpg", frame1, "image/jpeg")),
                ("frames", ("frame2.jpg", frame2, "image/jpeg")),
            ],
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["authId"] == "test-auth-123"
        assert data["passed"] is True
        assert data["livenessScore"] == 0.95
        assert data["nextStep"] == "COMPLETED"
    
    def test_liveness_missing_auth(self):
        frame1 = create_test_frame()
        frame2 = create_test_frame()
        
        response = client.post(
            "/kata/auth/liveness",
            files=[
                ("frames", ("frame1.jpg", frame1, "image/jpeg")),
                ("frames", ("frame2.jpg", frame2, "image/jpeg")),
            ],
        )
        
        assert response.status_code == 401
    
    def test_liveness_invalid_auth_format(self):
        frame1 = create_test_frame()
        frame2 = create_test_frame()
        
        response = client.post(
            "/kata/auth/liveness",
            headers={"Authorization": "Token invalid"},
            files=[
                ("frames", ("frame1.jpg", frame1, "image/jpeg")),
                ("frames", ("frame2.jpg", frame2, "image/jpeg")),
            ],
        )
        
        assert response.status_code == 401
    
    def test_liveness_invalid_token(self):
        frame1 = create_test_frame()
        frame2 = create_test_frame()
        
        response = client.post(
            "/kata/auth/liveness",
            headers={"Authorization": "Bearer invalid-token"},
            files=[
                ("frames", ("frame1.jpg", frame1, "image/jpeg")),
                ("frames", ("frame2.jpg", frame2, "image/jpeg")),
            ],
        )
        
        assert response.status_code == 401
    
    @patch("app.routers.liveness.verify_auth_token")
    def test_liveness_token_missing_auth_id(self, mock_verify):
        mock_verify.return_value = {
            "challenge_type": "BLINK",
            "doc_number": "12345678",
        }
        
        frame1 = create_test_frame()
        frame2 = create_test_frame()
        
        response = client.post(
            "/kata/auth/liveness",
            headers={"Authorization": "Bearer some-token"},
            files=[
                ("frames", ("frame1.jpg", frame1, "image/jpeg")),
                ("frames", ("frame2.jpg", frame2, "image/jpeg")),
            ],
        )
        
        assert response.status_code == 400
        assert "authId" in response.json()["detail"]
    
    @patch("app.routers.liveness.verify_auth_token")
    def test_liveness_token_missing_challenge_type(self, mock_verify):
        mock_verify.return_value = {
            "auth_id": "test-auth-123",
            "doc_number": "12345678",
        }
        
        frame1 = create_test_frame()
        frame2 = create_test_frame()
        
        response = client.post(
            "/kata/auth/liveness",
            headers={"Authorization": "Bearer some-token"},
            files=[
                ("frames", ("frame1.jpg", frame1, "image/jpeg")),
                ("frames", ("frame2.jpg", frame2, "image/jpeg")),
            ],
        )
        
        assert response.status_code == 400
        assert "challengeType" in response.json()["detail"]
    
    @patch("app.routers.liveness.verify_auth_token")
    def test_liveness_insufficient_frames(self, mock_verify):
        mock_verify.return_value = {
            "auth_id": "test-auth-123",
            "challenge_type": "BLINK",
            "doc_number": "12345678",
        }
        
        frame1 = create_test_frame()
        
        response = client.post(
            "/kata/auth/liveness",
            headers={"Authorization": "Bearer some-token"},
            files=[
                ("frames", ("frame1.jpg", frame1, "image/jpeg")),
            ],
        )
        
        assert response.status_code == 400
        assert "2 frames" in response.json()["detail"]
    
    @patch("app.routers.liveness.verify_auth_token")
    def test_liveness_empty_frame(self, mock_verify):
        mock_verify.return_value = {
            "auth_id": "test-auth-123",
            "challenge_type": "BLINK",
            "doc_number": "12345678",
        }
        
        frame1 = create_test_frame()
        empty_frame = BytesIO(b"")
        
        response = client.post(
            "/kata/auth/liveness",
            headers={"Authorization": "Bearer some-token"},
            files=[
                ("frames", ("frame1.jpg", frame1, "image/jpeg")),
                ("frames", ("frame2.jpg", empty_frame, "image/jpeg")),
            ],
        )
        
        assert response.status_code == 400
        assert "vacío" in response.json()["detail"]
    
    @patch("app.routers.liveness.evaluate_liveness")
    def test_liveness_failed(self, mock_evaluate):
        mock_evaluate.return_value = LivenessResult(
            auth_id="test-auth-123",
            challenge_type="BLINK",
            liveness_score=0.3,
            passed=False,
            reason="No se detectó parpadeo",
            next_step="REJECTED",
        )
        
        token = get_valid_token()
        frame1 = create_test_frame()
        frame2 = create_test_frame()
        
        response = client.post(
            "/kata/auth/liveness",
            headers={"Authorization": f"Bearer {token}"},
            files=[
                ("frames", ("frame1.jpg", frame1, "image/jpeg")),
                ("frames", ("frame2.jpg", frame2, "image/jpeg")),
            ],
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["passed"] is False
        assert data["nextStep"] == "REJECTED"
        assert data["reason"] == "No se detectó parpadeo"
    
    @patch("app.routers.liveness.evaluate_liveness")
    def test_liveness_service_error(self, mock_evaluate):
        mock_evaluate.side_effect = ValueError("Error en procesamiento")
        
        token = get_valid_token()
        frame1 = create_test_frame()
        frame2 = create_test_frame()
        
        response = client.post(
            "/kata/auth/liveness",
            headers={"Authorization": f"Bearer {token}"},
            files=[
                ("frames", ("frame1.jpg", frame1, "image/jpeg")),
                ("frames", ("frame2.jpg", frame2, "image/jpeg")),
            ],
        )
        
        assert response.status_code == 400
        assert "Error en procesamiento" in response.json()["detail"]
    
    @patch("app.routers.liveness.evaluate_liveness")
    def test_liveness_multiple_frames(self, mock_evaluate):
        mock_evaluate.return_value = LivenessResult(
            auth_id="test-auth-123",
            challenge_type="APPROACH",
            liveness_score=0.88,
            passed=True,
            reason=None,
            next_step="COMPLETED",
        )
        
        token = get_valid_token()
        frames = [create_test_frame() for _ in range(5)]
        
        response = client.post(
            "/kata/auth/liveness",
            headers={"Authorization": f"Bearer {token}"},
            files=[
                ("frames", (f"frame{i}.jpg", f, "image/jpeg"))
                for i, f in enumerate(frames)
            ],
        )
        
        assert response.status_code == 200
        mock_evaluate.assert_called_once()
        call_args = mock_evaluate.call_args
        assert len(call_args.kwargs["frames_bytes"]) == 5

