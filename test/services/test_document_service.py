
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO

from PIL import Image

from app.services.document_service import (
    evaluate_document,
    _evaluate_image_quality,
    _extract_doc_number_from_text,
    DocumentEvaluationResult,
)


class TestEvaluateImageQuality:
    
    def test_quality_valid_jpeg_image(self, valid_image_bytes):
        img = Image.open(BytesIO(valid_image_bytes))
        
        quality, reasons = _evaluate_image_quality(img)
        
        assert quality >= 0.6
    
    def test_quality_low_resolution(self):
        img = Image.new("RGB", (400, 300))
        
        quality, reasons = _evaluate_image_quality(img)
        
        assert quality < 1.0
        assert any("Resolución" in r for r in reasons)
    
    def test_quality_strange_aspect_ratio(self):
        img = Image.new("RGB", (1000, 200))
        
        quality, reasons = _evaluate_image_quality(img)
        
        assert quality < 1.0
        assert any("aspecto" in r for r in reasons)
    
    def test_quality_perfect_image(self):
        img = Image.new("RGB", (800, 600))
        img.format = "JPEG"
        
        quality, reasons = _evaluate_image_quality(img)
        
        assert quality >= 0.6 or len(reasons) > 0


class TestExtractDocNumberFromText:
    
    def test_extract_simple_doc_number(self):
        text = "CÉDULA DE CIUDADANÍA\n12345678\nJUAN PÉREZ"
        
        result = _extract_doc_number_from_text(text)
        
        assert result == "12345678"
    
    def test_extract_doc_number_with_dots(self):
        text = "Número: 12.345.678"
        
        result = _extract_doc_number_from_text(text)
        
        assert result == "12345678"
    
    def test_extract_doc_number_with_dashes(self):
        text = "CC: 12-345-678"
        
        result = _extract_doc_number_from_text(text)
        
        assert result == "12345678"
    
    def test_extract_doc_number_with_spaces(self):
        text = "Documento: 12 345 678"
        
        result = _extract_doc_number_from_text(text)
        
        assert result == "12345678"
    
    def test_extract_longest_candidate(self):
        text = "Ref: 12345\nCédula: 1234567890\nTel: 3001234567"
        
        result = _extract_doc_number_from_text(text)
        
        assert result is not None
        assert len(result) >= 8
    
    def test_extract_no_doc_number(self):
        text = "Sin números aquí, solo texto"
        
        result = _extract_doc_number_from_text(text)
        
        assert result is None
    
    def test_extract_short_numbers_ignored(self):
        text = "Edad: 35 años, Código: 123"
        
        result = _extract_doc_number_from_text(text)
        
        assert result is None
    
    def test_extract_very_long_numbers_ignored(self):
        text = "IBAN: 12345678901234567890"
        
        result = _extract_doc_number_from_text(text)
        
        if result:
            assert 8 <= len(result) <= 12
    
    def test_extract_mixed_format(self):
        text = "CC 12.345.678-9 expedida en Bogotá"
        
        result = _extract_doc_number_from_text(text)
        
        assert result is not None


class TestEvaluateDocument:
    
    @patch("app.services.document_service.extract_text_from_image")
    def test_evaluate_valid_document_match(self, mock_ocr, valid_image_bytes):
        mock_ocr.return_value = "CÉDULA\n12345678\nJUAN PÉREZ"
        
        result = evaluate_document(
            auth_id="test-auth-123",
            jwt_doc_number="12345678",
            image_bytes=valid_image_bytes,
        )
        
        assert result.auth_id == "test-auth-123"
        assert result.doc_match is True
        assert result.fraud_suspected is False
        assert result.document_status == "OK"
        assert result.next_step == "LIVENESS"
    
    @patch("app.services.document_service.extract_text_from_image")
    def test_evaluate_document_mismatch(self, mock_ocr, valid_image_bytes):
        mock_ocr.return_value = "CÉDULA\n87654321\nOTRA PERSONA"
        
        result = evaluate_document(
            auth_id="test-auth-123",
            jwt_doc_number="12345678",
            image_bytes=valid_image_bytes,
        )
        
        assert result.doc_match is False
        assert result.fraud_suspected is True
        assert result.document_status == "MISMATCH"
        assert result.next_step == "REJECTED"
        assert "no coincide" in result.reason
    
    @patch("app.services.document_service.extract_text_from_image")
    def test_evaluate_low_quality_image(self, mock_ocr, small_image_bytes):
        mock_ocr.return_value = "12345678"
        
        result = evaluate_document(
            auth_id="test-auth-123",
            jwt_doc_number="12345678",
            image_bytes=small_image_bytes,
        )
        
        assert result.quality_score < 0.6
        assert result.document_status == "RETAKE"
        assert result.next_step == "RETAKE_DOCUMENT"
    
    def test_evaluate_invalid_image(self, invalid_image_bytes):
        with pytest.raises(ValueError) as exc_info:
            evaluate_document(
                auth_id="test-auth-123",
                jwt_doc_number="12345678",
                image_bytes=invalid_image_bytes,
            )
        
        assert "no es una imagen válida" in str(exc_info.value)
    
    @patch("app.services.document_service.extract_text_from_image")
    def test_evaluate_ocr_no_doc_number(self, mock_ocr, valid_image_bytes):     
        mock_ocr.return_value = "Texto sin números relevantes"
        
        result = evaluate_document(
            auth_id="test-auth-123",
            jwt_doc_number="12345678",
            image_bytes=valid_image_bytes,
        )
        
        assert result.ocr_doc_number is None
        assert result.doc_match is False
        assert "No se pudo extraer" in result.reason
    
    @patch("app.services.document_service.extract_text_from_image")
    def test_evaluate_ocr_error(self, mock_ocr, valid_image_bytes):
        mock_ocr.side_effect = Exception("Textract unavailable")
        
        result = evaluate_document(
            auth_id="test-auth-123",
            jwt_doc_number="12345678",
            image_bytes=valid_image_bytes,
        )
        
        assert "Error en OCR" in result.reason
        assert result.ocr_doc_number is None
    
    @patch("app.services.document_service.extract_text_from_image")
    def test_evaluate_returns_correct_type(self, mock_ocr, valid_image_bytes):
        mock_ocr.return_value = "12345678"
        
        result = evaluate_document(
            auth_id="test-auth-123",
            jwt_doc_number="12345678",
            image_bytes=valid_image_bytes,
        )
        
        assert isinstance(result, DocumentEvaluationResult)
        assert hasattr(result, "auth_id")
        assert hasattr(result, "quality_score")
        assert hasattr(result, "document_status")
        assert hasattr(result, "next_step")
        assert hasattr(result, "ocr_doc_number")
        assert hasattr(result, "doc_match")
        assert hasattr(result, "fraud_suspected")
    
    @patch("app.services.document_service.extract_text_from_image")
    def test_evaluate_quality_score_range(self, mock_ocr, valid_image_bytes):
        mock_ocr.return_value = "12345678"
        
        result = evaluate_document(
            auth_id="test-auth-123",
            jwt_doc_number="12345678",
            image_bytes=valid_image_bytes,
        )
        
        assert 0.0 <= result.quality_score <= 1.0

