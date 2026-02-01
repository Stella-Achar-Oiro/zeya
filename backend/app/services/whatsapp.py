"""
WhatsApp Cloud API integration service.

Handles sending messages, parsing incoming webhooks, and media handling.
"""

import logging
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.schemas.webhook import WhatsAppMessage

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """Client for the WhatsApp Cloud API."""

    def __init__(self):
        self.api_url = f"{settings.WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}"
        self.headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

    async def send_text_message(self, to: str, text: str) -> dict[str, Any]:
        """Send a text message to a WhatsApp user."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
        return await self._send_request("/messages", payload)

    async def send_template_message(
        self, to: str, template_name: str, language: str = "en"
    ) -> dict[str, Any]:
        """Send a template message (for initiating conversations)."""
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
            },
        }
        return await self._send_request("/messages", payload)

    async def mark_as_read(self, message_id: str) -> dict[str, Any]:
        """Mark a message as read."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        return await self._send_request("/messages", payload)

    async def _send_request(self, endpoint: str, payload: dict) -> dict[str, Any]:
        """Send a request to the WhatsApp API with retry logic."""
        url = f"{self.api_url}{endpoint}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(3):
                try:
                    response = await client.post(
                        url, json=payload, headers=self.headers
                    )
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as e:
                    logger.error(
                        "WhatsApp API error (attempt %d): %s - %s",
                        attempt + 1,
                        e.response.status_code,
                        e.response.text,
                    )
                    if attempt == 2:
                        raise
                except httpx.RequestError as e:
                    logger.error(
                        "WhatsApp request error (attempt %d): %s", attempt + 1, str(e)
                    )
                    if attempt == 2:
                        raise
        return {}

    @staticmethod
    def parse_webhook_message(payload: dict) -> Optional[WhatsAppMessage]:
        """Parse an incoming WhatsApp webhook payload into a WhatsAppMessage."""
        try:
            entry = payload.get("entry", [])
            if not entry:
                return None

            changes = entry[0].get("changes", [])
            if not changes:
                return None

            value = changes[0].get("value", {})
            messages = value.get("messages", [])
            if not messages:
                return None

            msg = messages[0]
            contacts = value.get("contacts", [])
            from_number = msg.get("from", "")

            text = None
            if msg.get("type") == "text":
                text = msg.get("text", {}).get("body")

            return WhatsAppMessage(
                from_number=from_number,
                whatsapp_id=contacts[0]["wa_id"] if contacts else from_number,
                message_id=msg.get("id", ""),
                message_type=msg.get("type", "text"),
                text=text,
                timestamp=msg.get("timestamp", ""),
            )
        except (KeyError, IndexError) as e:
            logger.error("Failed to parse webhook message: %s", str(e))
            return None


whatsapp_client = WhatsAppClient()
