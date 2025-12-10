
from unittest.mock import patch, MagicMock

from app.services.ocr_service import extract_text_from_image


class TestExtractTextFromImage:
    
    @patch("app.services.ocr_service.textract")
    def test_extract_text_success(self, mock_textract, valid_image_bytes, mock_textract_response):
        mock_textract.detect_document_text.return_value = mock_textract_response
        
        result = extract_text_from_image(valid_image_bytes)
        
        assert "REPÚBLICA DE COLOMBIA" in result
        assert "CÉDULA DE CIUDADANÍA" in result
        assert "12345678" in result
        mock_textract.detect_document_text.assert_called_once()
    
    @patch("app.services.ocr_service.textract")
    def test_extract_text_empty_response(self, mock_textract, valid_image_bytes):
        mock_textract.detect_document_text.return_value = {"Blocks": []}
        
        result = extract_text_from_image(valid_image_bytes)
        
        assert result == ""
    
    @patch("app.services.ocr_service.textract")
    def test_extract_text_no_blocks_key(self, mock_textract, valid_image_bytes):
        mock_textract.detect_document_text.return_value = {}
        
        result = extract_text_from_image(valid_image_bytes)
        
        assert result == ""
    
    @patch("app.services.ocr_service.textract")
    def test_extract_text_only_line_blocks(self, mock_textract, valid_image_bytes):
        mock_textract.detect_document_text.return_value = {
            "Blocks": [
                {"BlockType": "PAGE", "Text": "No debe aparecer"},
                {"BlockType": "LINE", "Text": "Línea 1"},
                {"BlockType": "WORD", "Text": "No debe aparecer"},
                {"BlockType": "LINE", "Text": "Línea 2"},
            ]
        }
        
        result = extract_text_from_image(valid_image_bytes)
        
        assert "Línea 1" in result
        assert "Línea 2" in result
        assert "No debe aparecer" not in result
    
    @patch("app.services.ocr_service.textract")
    def test_extract_text_multiple_lines(self, mock_textract, valid_image_bytes):
        mock_textract.detect_document_text.return_value = {
            "Blocks": [
                {"BlockType": "LINE", "Text": "Primera línea"},
                {"BlockType": "LINE", "Text": "Segunda línea"},
                {"BlockType": "LINE", "Text": "Tercera línea"},
            ]
        }
        
        result = extract_text_from_image(valid_image_bytes)
        
        lines = result.split("\n")
        assert len(lines) == 3
        assert lines[0] == "Primera línea"
        assert lines[1] == "Segunda línea"
        assert lines[2] == "Tercera línea"
    
    @patch("app.services.ocr_service.textract")
    def test_extract_text_textract_error(self, mock_textract, valid_image_bytes):
        mock_textract.detect_document_text.side_effect = Exception("Textract error")
        
        with pytest.raises(Exception) as exc_info:
            extract_text_from_image(valid_image_bytes)
        
        assert "Textract error" in str(exc_info.value)
    
    @patch("app.services.ocr_service.textract")
    def test_extract_text_with_special_characters(self, mock_textract, valid_image_bytes):
        mock_textract.detect_document_text.return_value = {
            "Blocks": [
                {"BlockType": "LINE", "Text": "Número: 12.345.678-9"},
                {"BlockType": "LINE", "Text": "Dirección: Cra 50 # 10-20"},
                {"BlockType": "LINE", "Text": "Teléfono: +57 (300) 123-4567"},
            ]
        }
        
        result = extract_text_from_image(valid_image_bytes)
        
        assert "12.345.678-9" in result
        assert "Cra 50 # 10-20" in result
        assert "+57 (300) 123-4567" in result
    
    @patch("app.services.ocr_service.textract")
    def test_extract_text_called_with_correct_params(self, mock_textract, valid_image_bytes):
        mock_textract.detect_document_text.return_value = {"Blocks": []}
        
        extract_text_from_image(valid_image_bytes)
        
        mock_textract.detect_document_text.assert_called_once_with(
            Document={"Bytes": valid_image_bytes}
        )

