"""
Unit tests for WhatsApp webhook parsing.
"""

import pytest

from app.services.whatsapp import WhatsAppClient


class TestWebhookParsing:
    """Tests for WhatsAppClient.parse_webhook_message."""

    def test_parse_valid_text_message(self):
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "254700000000",
                                    "phone_number_id": "123456",
                                },
                                "contacts": [
                                    {
                                        "profile": {"name": "Test User"},
                                        "wa_id": "254712345678",
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": "254712345678",
                                        "id": "wamid.test123",
                                        "timestamp": "1706745600",
                                        "text": {"body": "Hello, I need help"},
                                        "type": "text",
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        message = WhatsAppClient.parse_webhook_message(payload)

        assert message is not None
        assert message.from_number == "254712345678"
        assert message.whatsapp_id == "254712345678"
        assert message.message_id == "wamid.test123"
        assert message.message_type == "text"
        assert message.text == "Hello, I need help"
        assert message.timestamp == "1706745600"

    def test_parse_empty_entry(self):
        payload = {"object": "whatsapp_business_account", "entry": []}
        result = WhatsAppClient.parse_webhook_message(payload)
        assert result is None

    def test_parse_no_messages(self):
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {},
                                "statuses": [{"id": "status1"}],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }
        result = WhatsAppClient.parse_webhook_message(payload)
        assert result is None

    def test_parse_image_message(self):
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "contacts": [{"wa_id": "254700000000"}],
                                "messages": [
                                    {
                                        "from": "254700000000",
                                        "id": "wamid.img1",
                                        "timestamp": "1706745600",
                                        "type": "image",
                                        "image": {"id": "img123"},
                                    }
                                ],
                            }
                        }
                    ],
                }
            ],
        }

        message = WhatsAppClient.parse_webhook_message(payload)
        assert message is not None
        assert message.message_type == "image"
        assert message.text is None

    def test_parse_malformed_payload(self):
        result = WhatsAppClient.parse_webhook_message({})
        assert result is None

    def test_parse_missing_contacts(self):
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "contacts": [],
                                "messages": [
                                    {
                                        "from": "254700000000",
                                        "id": "wamid.test",
                                        "timestamp": "123",
                                        "type": "text",
                                        "text": {"body": "test"},
                                    }
                                ],
                            }
                        }
                    ],
                }
            ],
        }
        message = WhatsAppClient.parse_webhook_message(payload)
        assert message is not None
        assert message.whatsapp_id == "254700000000"
