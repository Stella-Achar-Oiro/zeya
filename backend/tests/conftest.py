"""
Shared test fixtures.
"""

import pytest


@pytest.fixture
def sample_whatsapp_payload():
    """A valid WhatsApp webhook payload for testing."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "254700000000",
                                "phone_number_id": "PHONE_NUMBER_ID",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Mama Test"},
                                    "wa_id": "254712345678",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "254712345678",
                                    "id": "wamid.HBgLMjU0NzEyMzQ1Njc4FQIAERgS",
                                    "timestamp": "1706745600",
                                    "text": {
                                        "body": "What should I eat during pregnancy?"
                                    },
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


@pytest.fixture
def danger_sign_payload():
    """A WhatsApp webhook payload containing a danger sign message."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "254700000000",
                                "phone_number_id": "PHONE_NUMBER_ID",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Mama Test"},
                                    "wa_id": "254712345678",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "254712345678",
                                    "id": "wamid.DANGER123",
                                    "timestamp": "1706745700",
                                    "text": {
                                        "body": "I am having heavy bleeding and severe headache"
                                    },
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
