"""
Unit tests for security utilities.
"""

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
    verify_whatsapp_signature,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "test_password_123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_wrong_password(self):
        hashed = get_password_hash("correct_password")
        assert verify_password("wrong_password", hashed) is False


class TestJWT:
    def test_create_and_decode_token(self):
        data = {"sub": "testuser", "role": "admin"}
        token = create_access_token(data)
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "testuser"
        assert decoded["role"] == "admin"

    def test_invalid_token(self):
        result = decode_access_token("invalid.token.string")
        assert result is None

    def test_token_has_expiry(self):
        token = create_access_token({"sub": "user"})
        decoded = decode_access_token(token)
        assert "exp" in decoded


class TestWebhookSignature:
    def test_valid_signature(self):
        import hashlib
        import hmac
        from app.core.config import settings

        payload = b'{"test": "data"}'
        expected = hmac.new(
            settings.WHATSAPP_APP_SECRET.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        signature = f"sha256={expected}"

        # Only test if app secret is configured
        if settings.WHATSAPP_APP_SECRET:
            assert verify_whatsapp_signature(payload, signature) is True

    def test_invalid_signature(self):
        from app.core.config import settings

        if settings.WHATSAPP_APP_SECRET:
            assert (
                verify_whatsapp_signature(b"test", "sha256=invalid") is False
            )
