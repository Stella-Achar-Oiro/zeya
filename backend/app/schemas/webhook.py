from typing import Any, Optional

from pydantic import BaseModel


class WhatsAppMessage(BaseModel):
    """Parsed WhatsApp incoming message."""
    from_number: str
    whatsapp_id: str
    message_id: str
    message_type: str
    text: Optional[str] = None
    timestamp: str


class WhatsAppWebhookPayload(BaseModel):
    """Raw WhatsApp webhook payload."""
    object: str
    entry: list[dict[str, Any]]


class WebhookVerification(BaseModel):
    """WhatsApp webhook verification query parameters."""
    hub_mode: str
    hub_verify_token: str
    hub_challenge: str
