
import pytest
import json
from unittest.mock import patch, MagicMock

from app.services.liveness_service import (
    evaluate_liveness,
    _upload_frame_to_s3,
    _invoke_liveness_engine,
    LivenessResult,
)


class TestUploadFrameToS3:
    
    @patch("app.services.liveness_service.s3_client")
    def test_upload_frame_success(self, mock_s3):
        content = b"fake-image-bytes"
        
        _upload_frame_to_s3("test-bucket", "path/to/frame.jpg", content)
        
        mock_s3.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="path/to/frame.jpg",
            Body=content,
            ContentType="image/jpeg",
        )
    
    @patch("app.services.liveness_service.s3_client")
    def test_upload_frame_custom_content_type(self, mock_s3):
        content = b"fake-png-bytes"
        
        _upload_frame_to_s3("bucket", "frame.png", content, content_type="image/png")
        
        mock_s3.put_object.assert_called_once()
        call_args = mock_s3.put_object.call_args
        assert call_args.kwargs["ContentType"] == "image/png"


class TestInvokeLivenessEngine:
    
    @patch("app.services.liveness_service.lambda_client")
    def test_invoke_engine_success(self, mock_lambda):
        mock_payload = MagicMock()
        mock_payload.read.return_value = json.dumps({
            "statusCode": 200,
            "body": json.dumps({"livenessScore": 0.95, "passed": True})
        }).encode()
        mock_lambda.invoke.return_value = {"Payload": mock_payload}
        
        result = _invoke_liveness_engine(
            auth_id="test-123",
            challenge_type="BLINK",
            bucket="test-bucket",
            frame_keys=["frame_001.jpg", "frame_002.jpg"],
        )
        
        assert result["livenessScore"] == 0.95
        assert result["passed"] is True
    
    @patch("app.services.liveness_service.lambda_client")
    def test_invoke_engine_direct_response(self, mock_lambda):
        mock_payload = MagicMock()
        mock_payload.read.return_value = json.dumps({
            "livenessScore": 0.8,
            "passed": True,
            "reason": None
        }).encode()
        mock_lambda.invoke.return_value = {"Payload": mock_payload}
        
        result = _invoke_liveness_engine(
            auth_id="test-123",
            challenge_type="APPROACH",
            bucket="test-bucket",
            frame_keys=["frame_001.jpg"],
        )
        
        assert result["livenessScore"] == 0.8
    
    @patch("app.services.liveness_service.lambda_client")
    def test_invoke_engine_invalid_json(self, mock_lambda):
        mock_payload = MagicMock()
        mock_payload.read.return_value = b"not-valid-json"
        mock_lambda.invoke.return_value = {"Payload": mock_payload}
        
        with pytest.raises(ValueError) as exc_info:
            _invoke_liveness_engine(
                auth_id="test-123",
                challenge_type="BLINK",
                bucket="test-bucket",
                frame_keys=["frame.jpg"],
            )
        
        assert "Respuesta inválida" in str(exc_info.value)
    
    @patch("app.services.liveness_service.lambda_client")
    def test_invoke_engine_correct_payload(self, mock_lambda):
        mock_payload = MagicMock()
        mock_payload.read.return_value = json.dumps({"livenessScore": 0.9}).encode()
        mock_lambda.invoke.return_value = {"Payload": mock_payload}
        
        _invoke_liveness_engine(
            auth_id="auth-456",
            challenge_type="BLINK",
            bucket="my-bucket",
            frame_keys=["f1.jpg", "f2.jpg"],
        )
        
        mock_lambda.invoke.assert_called_once()
        call_args = mock_lambda.invoke.call_args
        payload_sent = json.loads(call_args.kwargs["Payload"].decode())
        
        assert payload_sent["authId"] == "auth-456"
        assert payload_sent["challengeType"] == "BLINK"
        assert payload_sent["bucket"] == "my-bucket"
        assert payload_sent["frameKeys"] == ["f1.jpg", "f2.jpg"]


class TestEvaluateLiveness:
    
    @patch("app.services.liveness_service._invoke_liveness_engine")
    @patch("app.services.liveness_service._upload_frame_to_s3")
    def test_evaluate_liveness_passed(self, mock_upload, mock_invoke, valid_image_bytes):
        mock_invoke.return_value = {
            "livenessScore": 0.95,
            "passed": True,
            "reason": None,
        }
        frames = [valid_image_bytes, valid_image_bytes]
        
        result = evaluate_liveness(
            auth_id="test-auth-123",
            challenge_type="BLINK",
            doc_number="12345678",
            frames_bytes=frames,
        )
        
        assert result.passed is True
        assert result.liveness_score == 0.95
        assert result.next_step == "COMPLETED"
        assert mock_upload.call_count == 2
    
    @patch("app.services.liveness_service._invoke_liveness_engine")
    @patch("app.services.liveness_service._upload_frame_to_s3")
    def test_evaluate_liveness_failed(self, mock_upload, mock_invoke, valid_image_bytes):
        mock_invoke.return_value = {
            "livenessScore": 0.3,
            "passed": False,
            "reason": "No se detectó parpadeo",
        }
        frames = [valid_image_bytes, valid_image_bytes]
        
        result = evaluate_liveness(
            auth_id="test-auth-123",
            challenge_type="BLINK",
            doc_number="12345678",
            frames_bytes=frames,
        )
        
        assert result.passed is False
        assert result.liveness_score == 0.3
        assert result.next_step == "REJECTED"
        assert result.reason == "No se detectó parpadeo"
    
    def test_evaluate_liveness_insufficient_frames(self, valid_image_bytes):
        with pytest.raises(ValueError) as exc_info:
            evaluate_liveness(
                auth_id="test-123",
                challenge_type="BLINK",
                doc_number="12345678",
                frames_bytes=[valid_image_bytes],
            )
        
        assert "al menos 2 frames" in str(exc_info.value)
    
    def test_evaluate_liveness_empty_frames(self):
        with pytest.raises(ValueError) as exc_info:
            evaluate_liveness(
                auth_id="test-123",
                challenge_type="BLINK",
                doc_number="12345678",
                frames_bytes=[],
            )
        
        assert "al menos 2 frames" in str(exc_info.value)
    
    @patch("app.services.liveness_service._invoke_liveness_engine")
    @patch("app.services.liveness_service._upload_frame_to_s3")
    def test_evaluate_liveness_unknown_doc_number(self, mock_upload, mock_invoke, valid_image_bytes):
        mock_invoke.return_value = {"livenessScore": 0.9, "passed": True}
        frames = [valid_image_bytes, valid_image_bytes]
        
        result = evaluate_liveness(
            auth_id="test-123",
            challenge_type="BLINK",
            doc_number=None,
            frames_bytes=frames,
        )
        
        call_args_list = mock_upload.call_args_list
        for call in call_args_list:
            key = call.args[1]
            assert "unknown-doc" in key
    
    @patch("app.services.liveness_service._invoke_liveness_engine")
    @patch("app.services.liveness_service._upload_frame_to_s3")
    def test_evaluate_liveness_returns_correct_type(self, mock_upload, mock_invoke, valid_image_bytes):
        mock_invoke.return_value = {"livenessScore": 0.9, "passed": True}
        frames = [valid_image_bytes, valid_image_bytes]
        
        result = evaluate_liveness(
            auth_id="test-123",
            challenge_type="APPROACH",
            doc_number="12345678",
            frames_bytes=frames,
        )
        
        assert isinstance(result, LivenessResult)
        assert result.auth_id == "test-123"
        assert result.challenge_type == "APPROACH"
    
    @patch("app.services.liveness_service._invoke_liveness_engine")
    @patch("app.services.liveness_service._upload_frame_to_s3")
    def test_evaluate_liveness_frame_keys_format(self, mock_upload, mock_invoke, valid_image_bytes):
        mock_invoke.return_value = {"livenessScore": 0.9, "passed": True}
        frames = [valid_image_bytes, valid_image_bytes, valid_image_bytes]
        
        evaluate_liveness(
            auth_id="auth-id-456",
            challenge_type="BLINK",
            doc_number="99999999",
            frames_bytes=frames,
        )
        
        call_args_list = mock_upload.call_args_list
        keys = [call.args[1] for call in call_args_list]
        
        assert "liveness/99999999/auth-id-456/frame_001.jpg" in keys
        assert "liveness/99999999/auth-id-456/frame_002.jpg" in keys
        assert "liveness/99999999/auth-id-456/frame_003.jpg" in keys

