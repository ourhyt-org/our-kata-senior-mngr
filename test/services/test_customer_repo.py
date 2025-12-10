
from unittest.mock import patch, MagicMock

import requests

from app.services.customer_repo import fetch_all_customers, get_customer_by_document


class TestFetchAllCustomers:
    
    @patch("app.services.customer_repo.requests.get")
    def test_fetch_all_customers_success(self, mock_get, sample_customer, blocked_customer):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [sample_customer, blocked_customer]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = fetch_all_customers()
        
        assert result is not None
        assert len(result) == 2
        assert result[0]["docNumber"] == sample_customer["docNumber"]
        mock_get.assert_called_once()
    
    @patch("app.services.customer_repo.requests.get")
    def test_fetch_all_customers_empty_list(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = fetch_all_customers()
        
        assert result == []
    
    @patch("app.services.customer_repo.requests.get")
    def test_fetch_all_customers_api_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("Connection error")
        
        result = fetch_all_customers()
        
        assert result is None
    
    @patch("app.services.customer_repo.requests.get")
    def test_fetch_all_customers_invalid_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "invalid"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = fetch_all_customers()
        
        assert result is None
    
    @patch("app.services.customer_repo.requests.get")
    def test_fetch_all_customers_timeout(self, mock_get):
        mock_get.side_effect = requests.Timeout("Request timeout")
        
        result = fetch_all_customers()
        
        assert result is None
    
    @patch("app.services.customer_repo.requests.get")
    def test_fetch_all_customers_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("Server error")
        mock_get.return_value = mock_response
        
        result = fetch_all_customers()
        
        assert result is None


class TestGetCustomerByDocument:
    
    @patch("app.services.customer_repo.fetch_all_customers")
    def test_get_customer_found(self, mock_fetch, sample_customer):
        mock_fetch.return_value = [sample_customer]
        
        result = get_customer_by_document("CC", "12345678")
        
        assert result is not None
        assert result["docNumber"] == "12345678"
        assert result["name"] == sample_customer["name"]
    
    @patch("app.services.customer_repo.fetch_all_customers")
    def test_get_customer_not_found(self, mock_fetch, sample_customer):
        mock_fetch.return_value = [sample_customer]
        
        result = get_customer_by_document("CC", "99999999")
        
        assert result is None
    
    @patch("app.services.customer_repo.fetch_all_customers")
    def test_get_customer_different_doc_type(self, mock_fetch, sample_customer):
        mock_fetch.return_value = [sample_customer]
        
        result = get_customer_by_document("CE", "12345678")
        
        assert result is None
    
    @patch("app.services.customer_repo.fetch_all_customers")
    def test_get_customer_empty_customers_list(self, mock_fetch):
        mock_fetch.return_value = []
        
        result = get_customer_by_document("CC", "12345678")
        
        assert result is None
    
    @patch("app.services.customer_repo.fetch_all_customers")
    def test_get_customer_fetch_failed(self, mock_fetch):
        mock_fetch.return_value = None
        
        result = get_customer_by_document("CC", "12345678")
        
        assert result is None
    
    @patch("app.services.customer_repo.fetch_all_customers")
    def test_get_customer_numeric_doc_number_comparison(self, mock_fetch):  
        customer_with_int = {
            "docType": "CC",
            "docNumber": 12345678,
            "name": "Test User",
        }
        mock_fetch.return_value = [customer_with_int]
        
        result = get_customer_by_document("CC", "12345678")
        
        assert result is not None
        assert str(result["docNumber"]) == "12345678"
    
    @patch("app.services.customer_repo.fetch_all_customers")
    def test_get_customer_multiple_customers(self, mock_fetch, sample_customer, blocked_customer):
        mock_fetch.return_value = [sample_customer, blocked_customer]
        
        result = get_customer_by_document("CC", "87654321")
        
        assert result is not None
        assert result["docNumber"] == "87654321"
        assert result["blocked"] is True

