"""
Conversation handler / orchestrator.

Coordinates the flow between WhatsApp messages, user management, danger sign
detection, AI engine, and database logging.
"""

import logging
import time
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import Conversation, MessageDirection
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.webhook import WhatsAppMessage
from app.services.ai_engine import ai_engine
from app.services.danger_signs import detect_danger_signs, get_emergency_response
from app.services.user_service import user_service
from app.services.whatsapp import whatsapp_client

logger = logging.getLogger(__name__)

# Registration flow states stored as simple strings
STATE_AWAITING_CONSENT = "awaiting_consent"
STATE_AWAITING_NAME = "awaiting_name"
STATE_AWAITING_GESTATIONAL_AGE = "awaiting_gestational_age"
STATE_REGISTERED = "registered"

WELCOME_MESSAGE_EN = (
    "Welcome to the Antenatal Education Chatbot! I am here to help you with "
    "information about your pregnancy journey.\n\n"
    "This is a research study chatbot that provides educational information about "
    "maternal health based on WHO and Kenya Ministry of Health guidelines.\n\n"
    "Important: This is educational information, not medical diagnosis. Always "
    "consult your healthcare provider for medical advice.\n\n"
    "Do you consent to participate in this study and receive antenatal education "
    "messages? Please reply YES or NO."
)

WELCOME_MESSAGE_SW = (
    "Karibu kwenye Chatbot ya Elimu ya Ujauzito! Niko hapa kukusaidia na "
    "habari kuhusu safari yako ya ujauzito.\n\n"
    "Hii ni chatbot ya utafiti inayotoa habari za kielimu kuhusu afya ya mama "
    "kulingana na miongozo ya WHO na Wizara ya Afya ya Kenya.\n\n"
    "Muhimu: Hii ni habari ya kielimu, si utambuzi wa kimatibabu. Daima "
    "wasiliana na mtoa huduma wako wa afya kwa ushauri wa kimatibabu.\n\n"
    "Je, unakubali kushiriki katika utafiti huu na kupokea ujumbe wa elimu ya "
    "ujauzito? Tafadhali jibu NDIYO au HAPANA."
)


class ConversationHandler:
    """Orchestrates the full conversation flow."""

    async def handle_incoming_message(
        self, db: AsyncSession, message: WhatsAppMessage
    ) -> None:
        """
        Process an incoming WhatsApp message end-to-end.

        1. Look up or create user
        2. Handle registration flow if not complete
        3. Detect danger signs
        4. Generate AI response
        5. Send response via WhatsApp
        6. Log everything to the database
        """
        if not message.text:
            # Only handle text messages for now
            return

        start_time = time.time()

        # Mark message as read
        try:
            await whatsapp_client.mark_as_read(message.message_id)
        except Exception as e:
            logger.warning("Failed to mark message as read: %s", str(e))

        # Look up user
        user = await user_service.get_by_whatsapp_id(db, message.whatsapp_id)

        if user is None:
            # New user - create and start registration
            user = await self._create_new_user(db, message)
            await self._send_welcome(user)
            return

        if not user.is_active:
            return

        # Log incoming message
        incoming_log = await self._log_message(
            db,
            user=user,
            direction=MessageDirection.INCOMING,
            text=message.text,
        )

        # Handle registration flow
        if not user.registration_complete:
            await self._handle_registration(db, user, message.text)
            return

        # Detect danger signs
        danger_result = detect_danger_signs(message.text)

        # Generate response
        if danger_result.detected:
            # Send emergency response immediately with database facility lookup
            # Default to Migori County - can be extended to support user location
            emergency_msg = await get_emergency_response(
                db=db, county="Migori", language=user.language_preference
            )
            await whatsapp_client.send_text_message(user.phone_number, emergency_msg)

            # Also get AI response for additional context
            ai_response = await ai_engine.generate_response(
                user_message=message.text,
                user_id=str(user.id),
                gestational_age=user.current_gestational_age(),
                language=user.language_preference,
                is_danger_sign=True,
            )
            # Append AI response if it adds value
            if ai_response and len(ai_response) > 20:
                await whatsapp_client.send_text_message(
                    user.phone_number, ai_response
                )
            response_text = emergency_msg + "\n\n" + ai_response
        else:
            ai_response = await ai_engine.generate_response(
                user_message=message.text,
                user_id=str(user.id),
                gestational_age=user.current_gestational_age(),
                language=user.language_preference,
                is_danger_sign=False,
            )
            await whatsapp_client.send_text_message(user.phone_number, ai_response)
            response_text = ai_response

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Log outgoing message
        await self._log_message(
            db,
            user=user,
            direction=MessageDirection.OUTGOING,
            text=response_text,
            danger_sign_detected=danger_result.detected,
            danger_sign_keywords=", ".join(danger_result.keywords) if danger_result.keywords else None,
            response_time_ms=elapsed_ms,
        )

    async def _create_new_user(
        self, db: AsyncSession, message: WhatsAppMessage
    ) -> User:
        """Create a new user from an incoming message."""
        user_data = UserCreate(
            phone_number=message.from_number,
            whatsapp_id=message.whatsapp_id,
        )
        user = await user_service.create_user(db, user_data)
        logger.info("New user created: %s", user.whatsapp_id)
        return user

    async def _send_welcome(self, user: User) -> None:
        """Send the welcome/consent message."""
        msg = WELCOME_MESSAGE_SW if user.language_preference == "sw" else WELCOME_MESSAGE_EN
        try:
            await whatsapp_client.send_text_message(user.phone_number, msg)
        except Exception as e:
            logger.error("Failed to send welcome message: %s", str(e))

    async def _handle_registration(
        self, db: AsyncSession, user: User, text: str
    ) -> None:
        """Handle the multi-step registration flow."""
        text_lower = text.strip().lower()

        if not user.consent_given:
            # Awaiting consent
            if text_lower in ("yes", "ndiyo", "ndio"):
                await user_service.update_user(
                    db, user, UserUpdate(consent_given=True)
                )
                msg = (
                    "Thank you for consenting to participate! "
                    "What is your name?"
                )
                await whatsapp_client.send_text_message(user.phone_number, msg)
            elif text_lower in ("no", "hapana"):
                msg = (
                    "Thank you for your response. You can message us anytime "
                    "if you change your mind. Take care, Mama!"
                )
                await whatsapp_client.send_text_message(user.phone_number, msg)
                await user_service.deactivate_user(db, user)
            else:
                msg = "Please reply YES or NO to consent to participate in the study."
                await whatsapp_client.send_text_message(user.phone_number, msg)
            return

        if user.name is None:
            # Awaiting name
            await user_service.update_user(db, user, UserUpdate(name=text.strip()))
            msg = (
                f"Nice to meet you, {text.strip()}! "
                "How many weeks pregnant are you? "
                "Please reply with a number (for example: 20)."
            )
            await whatsapp_client.send_text_message(user.phone_number, msg)
            return

        if user.gestational_age_at_enrollment is None:
            # Awaiting gestational age
            try:
                weeks = int(text_lower.strip().split()[0])
                if weeks < 1 or weeks > 42:
                    raise ValueError("Out of range")
            except (ValueError, IndexError):
                msg = (
                    "Please enter a valid number of weeks (between 1 and 42). "
                    "For example: 20"
                )
                await whatsapp_client.send_text_message(user.phone_number, msg)
                return

            await user_service.set_gestational_age(db, user, weeks)
            await user_service.update_user(
                db, user, UserUpdate(registration_complete=True)
            )

            msg = (
                f"You are registered! You are {weeks} weeks pregnant. "
                f"Your expected delivery date is approximately "
                f"{user.expected_delivery_date.strftime('%B %d, %Y') if user.expected_delivery_date else 'to be determined'}.\n\n"
                "You can now ask me any questions about your pregnancy. "
                "I can help with:\n"
                "- Nutrition and diet\n"
                "- Danger signs to watch for\n"
                "- Birth preparedness\n"
                "- Common discomforts\n"
                "- ANC appointments\n"
                "- Newborn care\n\n"
                "Just type your question and I will do my best to help you, Mama!"
            )
            await whatsapp_client.send_text_message(user.phone_number, msg)
            return

    async def _log_message(
        self,
        db: AsyncSession,
        user: User,
        direction: MessageDirection,
        text: str,
        danger_sign_detected: bool = False,
        danger_sign_keywords: Optional[str] = None,
        response_time_ms: Optional[int] = None,
    ) -> Conversation:
        """Log a conversation message to the database."""
        conversation = Conversation(
            user_id=user.id,
            message_direction=direction,
            message_text=text,
            gestational_age_at_message=user.current_gestational_age(),
            danger_sign_detected=danger_sign_detected,
            danger_sign_keywords=danger_sign_keywords,
            response_time_ms=response_time_ms,
            ai_model_used=settings.GEMINI_MODEL if direction == MessageDirection.OUTGOING else None,
        )
        db.add(conversation)
        await db.flush()
        return conversation


conversation_handler = ConversationHandler()
