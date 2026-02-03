"""
AI Conversation Engine using Google Gemini.

Handles prompt engineering, context injection, conversation history management,
and response validation for maternal health education.
"""

import json
import logging
import time
from typing import Optional

from google import genai

from app.core.config import settings
from app.core.redis import redis_client

logger = logging.getLogger(__name__)

# Configure Gemini client
client = genai.Client(api_key=settings.GEMINI_API_KEY)

SYSTEM_PROMPT = """You are a maternal health education assistant serving pregnant women \
in rural Kenya. Your role is to provide accurate, culturally appropriate antenatal \
information based on WHO and Kenya Ministry of Health guidelines.

CRITICAL RULES:
1. If you detect ANY danger sign (bleeding, severe headache, reduced fetal movement, \
convulsions, high fever, severe abdominal pain, water breaking, swelling of face/hands), \
IMMEDIATELY advise seeking urgent medical care at the nearest health facility.
2. Never diagnose conditions or prescribe treatments.
3. Always encourage ANC (antenatal care) attendance and completing all recommended visits.
4. Keep responses under 200 words for readability on mobile phones.
5. Use simple, clear language appropriate for secondary school education level.
6. Be culturally sensitive to practices in rural Kenya while correcting harmful myths.
7. When unsure about medical specifics, advise consulting a healthcare provider.

CONTENT AREAS YOU CAN HELP WITH:
- Danger signs recognition and when to seek emergency care
- Nutrition and dietary guidance during pregnancy
- Physical activity recommendations
- Birth preparedness and complication readiness
- Common pregnancy discomforts and safe management
- ANC appointment importance and schedule
- Newborn care preparation
- Breastfeeding education

DISCLAIMER: Include this reminder periodically:
"This is educational information, not medical diagnosis. Always consult your healthcare \
provider for medical advice."

Respond in a warm, supportive tone. Address the user as "Mama" when appropriate. \
If the user writes in Swahili, respond in Swahili. If in English, respond in English."""

GESTATIONAL_GUIDANCE = {
    (1, 12): "First trimester: Focus on nutrition (folate, iron), managing morning sickness, "
    "first ANC visit importance, and avoiding harmful substances.",
    (13, 26): "Second trimester: Focus on balanced diet, fetal movement awareness, "
    "anomaly screening, dental care, and preparing for birth.",
    (27, 40): "Third trimester: Focus on birth preparedness, recognizing labor signs, "
    "danger signs awareness, breastfeeding preparation, and newborn care.",
}

# Maximum conversation turns to include in context
MAX_CONTEXT_TURNS = 6


class AIEngine:
    """Conversation engine powered by Google Gemini."""

    def __init__(self):
        self.model_name = settings.GEMINI_MODEL

    async def generate_response(
        self,
        user_message: str,
        user_id: str,
        gestational_age: Optional[int] = None,
        language: str = "en",
        is_danger_sign: bool = False,
    ) -> str:
        """
        Generate an AI response for a user message.

        Args:
            user_message: The incoming message from the user.
            user_id: Unique user identifier for conversation history.
            gestational_age: Current gestational age in weeks.
            language: Preferred language (en or sw).
            is_danger_sign: Whether danger signs were detected in the message.

        Returns:
            The AI-generated response text.
        """
        start_time = time.time()

        try:
            context = await self._build_context(
                user_id, gestational_age, language, is_danger_sign
            )
            history = await self._get_conversation_history(user_id)

            prompt_parts = [SYSTEM_PROMPT, context]
            if history:
                prompt_parts.append(
                    "Recent conversation history:\n" + "\n".join(history)
                )
            prompt_parts.append(f"User message: {user_message}")

            full_prompt = "\n\n".join(prompt_parts)

            response = client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
            )

            if response and response.text:
                ai_response = response.text.strip()
            else:
                ai_response = self._get_fallback_response(language)

            # Store conversation turn in Redis for context
            await self._store_conversation_turn(user_id, user_message, ai_response)

            elapsed = time.time() - start_time
            logger.info(
                "AI response generated in %.2fs for user %s", elapsed, user_id
            )

            return ai_response

        except Exception as e:
            logger.error("AI generation error for user %s: %s", user_id, str(e))
            return self._get_fallback_response(language)

    async def _build_context(
        self,
        user_id: str,
        gestational_age: Optional[int],
        language: str,
        is_danger_sign: bool,
    ) -> str:
        """Build context injection string for the prompt."""
        parts = []

        if gestational_age is not None:
            parts.append(f"User's current gestational age: {gestational_age} weeks.")
            for (start, end), guidance in GESTATIONAL_GUIDANCE.items():
                if start <= gestational_age <= end:
                    parts.append(f"Trimester guidance: {guidance}")
                    break

        if language == "sw":
            parts.append("User prefers Swahili. Respond in Swahili.")

        if is_danger_sign:
            parts.append(
                "ALERT: Danger sign keywords detected in the user's message. "
                "Prioritize advising immediate medical care before any other information."
            )

        return "\n".join(parts) if parts else "No additional context available."

    async def _get_conversation_history(self, user_id: str) -> list[str]:
        """Retrieve recent conversation history from Redis."""
        try:
            history_key = f"chat_history:{user_id}"
            history_raw = await redis_client.lrange(history_key, 0, MAX_CONTEXT_TURNS - 1)
            return [item for item in history_raw] if history_raw else []
        except Exception as e:
            logger.warning("Failed to get conversation history: %s", str(e))
            return []

    async def _store_conversation_turn(
        self, user_id: str, user_message: str, ai_response: str
    ) -> None:
        """Store a conversation turn in Redis for context window."""
        try:
            history_key = f"chat_history:{user_id}"
            turn = json.dumps(
                {"user": user_message, "assistant": ai_response},
                ensure_ascii=False,
            )
            formatted = f"User: {user_message}\nAssistant: {ai_response}"
            await redis_client.lpush(history_key, formatted)
            await redis_client.ltrim(history_key, 0, MAX_CONTEXT_TURNS - 1)
            # Expire conversation history after 24 hours of inactivity
            await redis_client.expire(history_key, 86400)
        except Exception as e:
            logger.warning("Failed to store conversation turn: %s", str(e))

    @staticmethod
    def _get_fallback_response(language: str = "en") -> str:
        """Return a fallback response when AI generation fails."""
        if language == "sw":
            return (
                "Samahani, siwezi kukusaidia kwa wakati huu. Tafadhali jaribu tena baadaye. "
                "Ikiwa una dharura ya kimatibabu, tafadhali nenda hospitali iliyo karibu nawe mara moja."
            )
        return (
            "I am sorry, I am unable to help right now. Please try again later. "
            "If you have a medical emergency, please go to your nearest health facility immediately."
        )


ai_engine = AIEngine()
