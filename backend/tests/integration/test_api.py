"""
Integration tests for API endpoints.

These tests use the FastAPI TestClient and require no external services.
They test the HTTP layer including routing, request validation, and response formats.
"""

import pytest
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "antenatal-chatbot"


class TestWebhookVerification:
    def test_valid_verification(self, client):
        response = client.get(
            "/api/v1/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "",  # matches default empty config
                "hub.challenge": "test_challenge_123",
            },
        )
        assert response.status_code == 200
        assert response.text == "test_challenge_123"

    def test_invalid_verification_token(self, client):
        with patch("app.api.endpoints.webhook.settings") as mock_settings:
            mock_settings.WHATSAPP_VERIFY_TOKEN = "correct_token"
            response = client.get(
                "/api/v1/webhook",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "wrong_token",
                    "hub.challenge": "challenge",
                },
            )
            assert response.status_code == 403


class TestWebhookReceive:
    def test_webhook_with_status_update(self, client):
        """Status updates (not messages) should return ok."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {},
                                "statuses": [{"id": "status1"}],
                            }
                        }
                    ],
                }
            ],
        }
        response = client.post("/api/v1/webhook", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestAuthEndpoints:
    def test_login_without_credentials(self, client):
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422  # Validation error

    def test_protected_endpoint_without_token(self, client):
        response = client.get("/api/v1/users")
        # HTTPBearer returns 403 when no Authorization header is present
        assert response.status_code in (401, 403)

    def test_protected_endpoint_with_invalid_token(self, client):
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401
