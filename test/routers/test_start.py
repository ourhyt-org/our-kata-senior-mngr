
import os
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
    
os.environ["JWT_SECRET_SECRET_NAME"] = "test-secret-key-for-jwt-testing"

from app.main import app

client = TestClient(app)


class TestStartEndpoint:
    
    @patch("app.routers.start.get_customer_by_document")
    @patch("app.routers.start.random.choice")
    def test_start_success(self, mock_random, mock_get_customer, sample_customer):
        mock_get_customer.return_value = sample_customer
        mock_random.return_value = "BLINK"
        
        response = client.post(
            "/kata/auth/start",
            json={
                "docType": "CC",
                "docNumber": "12345678",
                "phone": "3001234567",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "authId" in data
        assert "token" in data
        assert data["token"] != ""
        assert data["nextStep"] == "DOCUMENT"
        assert data["customerStatus"] == "ACTIVE"
        assert data["challengeType"] == "BLINK"
    
    @patch("app.routers.start.get_customer_by_document")
    def test_start_customer_not_found(self, mock_get_customer):
        mock_get_customer.return_value = None
        
        response = client.post(
            "/kata/auth/start",
            json={
                "docType": "CC",
                "docNumber": "99999999",
                "phone": "3001234567",
            },
        )
        
        assert response.status_code == 403
        assert "no registrado" in response.json()["detail"]
    
    @patch("app.routers.start.get_customer_by_document")
    def test_start_customer_blocked(self, mock_get_customer, blocked_customer):
        mock_get_customer.return_value = blocked_customer
        
        response = client.post(
            "/kata/auth/start",
            json={
                "docType": "CC",
                "docNumber": "87654321",
                "phone": "3009876543",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["nextStep"] == "REJECTED"
        assert data["token"] == ""
        assert data["challengeType"] == "NONE"
    
    @patch("app.routers.start.get_customer_by_document")
    def test_start_high_risk_customer(self, mock_get_customer, high_risk_customer):
        mock_get_customer.return_value = high_risk_customer
        
        response = client.post(
            "/kata/auth/start",
            json={
                "docType": "CC",
                "docNumber": "11111111",
                "phone": "3001111111",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["nextStep"] == "REJECTED"
        assert data["riskScore"] > 0.8
    
    def test_start_missing_doc_type(self):
        response = client.post(
            "/kata/auth/start",
            json={
                "docNumber": "12345678",
                "phone": "3001234567",
            },
        )
        
        assert response.status_code == 422
    
    def test_start_missing_doc_number(self):
        response = client.post(
            "/kata/auth/start",
            json={
                "docType": "CC",
                "phone": "3001234567",
            },
        )
        
        assert response.status_code == 422
    
    def test_start_missing_phone(self):
        response = client.post(
            "/kata/auth/start",
            json={
                "docType": "CC",
                "docNumber": "12345678",
            },
        )
        
        assert response.status_code == 422
    
    @patch("app.routers.start.get_customer_by_document")
    @patch("app.routers.start.random.choice")
    def test_start_returns_customer_name(self, mock_random, mock_get_customer, sample_customer):
        mock_get_customer.return_value = sample_customer
        mock_random.return_value = "APPROACH"
        
        response = client.post(
            "/kata/auth/start",
            json={
                "docType": "CC",
                "docNumber": "12345678",
                "phone": "3001234567",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Juan Pérez"
    
    @patch("app.routers.start.get_customer_by_document")
    @patch("app.routers.start.random.choice")
    def test_start_returns_allowed_products(self, mock_random, mock_get_customer, sample_customer):
        mock_get_customer.return_value = sample_customer
        mock_random.return_value = "BLINK"
        
        response = client.post(
            "/kata/auth/start",
            json={
                "docType": "CC",
                "docNumber": "12345678",
                "phone": "3001234567",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "CREDIT" in data["allowedProducts"]
        assert "SAVINGS" in data["allowedProducts"]
    
    @patch("app.routers.start.get_customer_by_document")
    def test_start_risk_score_at_boundary(self, mock_get_customer):
        customer = {
            "docType": "CC",
            "docNumber": "12345678",
            "name": "Cliente Límite",
            "phone": "3001234567",
            "status": "ACTIVE",
            "blocked": False,
            "riskScore": 0.8,
            "reason": None,
            "allowedProducts": ["SAVINGS"],
        }
        mock_get_customer.return_value = customer
        
        response = client.post(
            "/kata/auth/start",
            json={
                "docType": "CC",
                "docNumber": "12345678",
                "phone": "3001234567",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["nextStep"] == "DOCUMENT"

