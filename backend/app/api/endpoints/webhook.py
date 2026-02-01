"""
WhatsApp webhook endpoints.

Handles incoming messages from the WhatsApp Cloud API and webhook verification.
"""

import logging

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_whatsapp_signature
from app.services.conversation_handler import conversation_handler
from app.services.whatsapp import WhatsAppClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
) -> Response:
    """
    WhatsApp webhook verification endpoint.

    Meta sends a GET request with a verify token to confirm the webhook URL.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return Response(content=hub_challenge, media_type="text/plain")

    logger.warning("Webhook verification failed: invalid token")
    return Response(status_code=status.HTTP_403_FORBIDDEN)


@router.post("", status_code=status.HTTP_200_OK)
async def receive_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_hub_signature_256: str = Header(default=""),
) -> dict:
    """
    Receive incoming WhatsApp messages.

    Verifies the webhook signature, parses the message, and delegates
    processing to the conversation handler.
    """
    body = await request.body()

    # Verify signature if app secret is configured
    if settings.WHATSAPP_APP_SECRET:
        if not verify_whatsapp_signature(body, x_hub_signature_256):
            logger.warning("Invalid webhook signature")
            return {"status": "error", "message": "Invalid signature"}

    payload = await request.json()

    # Parse message
    message = WhatsAppClient.parse_webhook_message(payload)
    if message is None:
        # Could be a status update or other non-message event
        return {"status": "ok"}

    # Process message
    try:
        await conversation_handler.handle_incoming_message(db, message)
    except Exception as e:
        logger.error("Error processing message: %s", str(e), exc_info=True)
        # Return 200 to prevent WhatsApp from retrying
        return {"status": "error", "message": "Processing failed"}

    return {"status": "ok"}
