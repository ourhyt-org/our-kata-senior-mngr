
import pytest
import os

os.environ["JWT_SECRET_SECRET_NAME"] = "test-secret-key-for-jwt-testing"

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestAppConfiguration:
    
    def test_app_title(self):
        assert app.title == "Kata Authentication Service"
    
    def test_app_version(self):
        assert app.version == "1.0.0"
    
    def test_app_description(self):
        assert "OCR" in app.description
        assert "Liveness" in app.description


class TestRoutersIncluded:
    
    def test_start_router_included(self):
        routes = [route.path for route in app.routes]
        assert "/kata/auth/start" in routes
    
    def test_document_router_included(self):
        routes = [route.path for route in app.routes]
        assert "/kata/auth/document" in routes
    
    def test_liveness_router_included(self):
        routes = [route.path for route in app.routes]
        assert "/kata/auth/liveness" in routes


class TestOpenAPISchema:
    
    def test_openapi_available(self):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "Kata Authentication Service"
    
    def test_docs_endpoint_available(self):
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_redoc_endpoint_available(self):
        response = client.get("/redoc")
        assert response.status_code == 200


class TestHealthCheck:
    
    def test_app_responds(self):
        response = client.post("/kata/auth/start", json={})
        assert response.status_code == 422
    
    def test_unknown_endpoint_returns_404(self):
        response = client.get("/unknown/endpoint")
        assert response.status_code == 404


class TestMangumHandler:
    
    def test_mangum_handler_exists(self):
        from app.main import handler
        assert handler is not None
    
    def test_mangum_handler_is_callable(self):
        from app.main import handler
        assert callable(handler)

