"""
The registration node ports ConversationHandler._handle_registration and
AIEngine._build_context to participant data.

Participant data keys mirror the Zeya User columns: consent_given, consent_given_at,
name, gestational_age_at_enrollment, expected_delivery_date, enrolled_at,
registration_complete, language_preference, study_group.
"""

import datetime

import pytest

from ocs.tests.conftest import BACKEND, module_constant, node_source
from ocs.tests.sandbox import NodeHarness

NOW = datetime.datetime(2026, 10, 3, 9, 30, tzinfo=datetime.UTC)

WELCOME_EN = module_constant("app/services/conversation_handler.py", "WELCOME_MESSAGE_EN")
WELCOME_SW = module_constant("app/services/conversation_handler.py", "WELCOME_MESSAGE_SW")
GESTATIONAL_GUIDANCE = module_constant("app/services/ai_engine.py", "GESTATIONAL_GUIDANCE")

CONSENTED_MSG = "Thank you for consenting to participate! What is your name?"
DECLINED_MSG = "Thank you for your response. You can message us anytime if you change your mind. Take care, Mama!"
CONSENT_RETRY_MSG = "Please reply YES or NO to consent to participate in the study."
GA_RETRY_MSG = "Please enter a valid number of weeks (between 1 and 42). For example: 20"

REGISTERED = {
    "welcome_sent": True,
    "enrolled_at": "2026-09-23T09:30:00+00:00",  # 10 days before NOW
    "consent_given": True,
    "name": "Akinyi",
    "name_collected": True,
    "gestational_age_at_enrollment": 20,
    "registration_complete": True,
    "language_preference": "en",
    "study_group": "intervention",
}


def _run(message: str, participant_data: dict | None = None) -> NodeHarness:
    harness = NodeHarness(node_source("registration"), participant_data=participant_data, now=NOW)
    harness.output = harness.run(message)
    return harness


def _after(*messages: str) -> NodeHarness:
    data: dict = {}
    harness = None
    for message in messages:
        harness = _run(message, data)
        data = harness.participant_data
    return harness


def test_reply_strings_exist_in_zeya_source():
    source = (BACKEND / "app/services/conversation_handler.py").read_text()
    for fragment in [
        "Thank you for consenting to participate! ",
        "What is your name?",
        "Thank you for your response. You can message us anytime ",
        "if you change your mind. Take care, Mama!",
        CONSENT_RETRY_MSG,
        "Please enter a valid number of weeks (between 1 and 42). ",
        "How many weeks pregnant are you? ",
        "Please reply with a number (for example: 20).",
        "Just type your question and I will do my best to help you, Mama!",
    ]:
        assert fragment in source, fragment


class TestFirstContact:
    def test_sends_english_welcome_and_enrols(self):
        harness = _run("Hi")

        assert harness.output == WELCOME_EN
        assert harness.temp_state["registration_route"] == "REPLY"
        assert harness.participant_data == {
            "welcome_sent": True,
            "enrolled_at": NOW.isoformat(),
            "consent_given": False,
            "registration_complete": False,
            "language_preference": "en",
            "study_group": "intervention",
        }
        assert harness.message_tags == ["registration", "registration:first_contact"]

    def test_message_content_is_ignored(self):
        # Zeya ignored the first message, even "yes".
        harness = _run("yes")
        assert harness.output == WELCOME_EN
        assert harness.participant_data["consent_given"] is False

    def test_keeps_seeded_language_and_group(self):
        harness = _run("Habari", {"language_preference": "sw", "study_group": "control"})

        assert harness.output == WELCOME_SW
        assert harness.participant_data["language_preference"] == "sw"
        assert harness.participant_data["study_group"] == "control"


class TestConsent:
    @pytest.mark.parametrize("answer", ["yes", "YES", " Ndiyo ", "ndio"])
    def test_accepts(self, answer):
        harness = _after("Hi", answer)

        assert harness.output == CONSENTED_MSG
        assert harness.participant_data["consent_given"] is True
        assert harness.participant_data["consent_given_at"] == NOW.isoformat()
        assert harness.message_tags == ["registration"]

    @pytest.mark.parametrize("answer", ["no", "Hapana"])
    def test_declines(self, answer):
        harness = _after("Hi", answer)

        assert harness.output == DECLINED_MSG
        assert harness.participant_data["consent_given"] is False
        assert harness.participant_data["consent_declined"] is True

    def test_can_consent_after_declining(self):
        harness = _after("Hi", "no", "yes")

        assert harness.output == CONSENTED_MSG
        assert harness.participant_data["consent_given"] is True

    @pytest.mark.parametrize("answer", ["maybe", "yes please", ""])
    def test_reprompts_on_anything_else(self, answer):
        harness = _after("Hi", answer)

        assert harness.output == CONSENT_RETRY_MSG
        assert harness.participant_data["consent_given"] is False


class TestName:
    def test_stores_stripped_name(self):
        harness = _after("Hi", "yes", "  Akinyi Otieno ")

        assert harness.participant_data["name"] == "Akinyi Otieno"
        assert harness.participant_data["name_collected"] is True
        assert harness.output == (
            "Nice to meet you, Akinyi Otieno! How many weeks pregnant are you? "
            "Please reply with a number (for example: 20)."
        )

    def test_asks_for_name_even_if_ocs_already_has_one(self):
        # OCS exposes participant.name as participant data "name".
        consented = _after("Hi", "yes").participant_data | {"name": "+254700000000"}

        harness = _run("Akinyi", consented)

        assert harness.output.startswith("Nice to meet you, Akinyi!")
        assert harness.participant_data["name"] == "Akinyi"


class TestGestationalAge:
    @pytest.mark.parametrize(("answer", "weeks"), [("20", 20), ("20 weeks", 20), (" 1 ", 1), ("42", 42)])
    def test_completes_registration(self, answer, weeks):
        harness = _after("Hi", "yes", "Akinyi", answer)

        edd = NOW.date() + datetime.timedelta(weeks=40 - weeks)
        assert harness.participant_data["gestational_age_at_enrollment"] == weeks
        assert harness.participant_data["expected_delivery_date"] == edd.isoformat()
        assert harness.participant_data["registration_complete"] is True
        assert harness.output == (
            f"You are registered! You are {weeks} weeks pregnant. "
            f"Your expected delivery date is approximately {edd.strftime('%B %d, %Y')}.\n\n"
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

    @pytest.mark.parametrize("answer", ["twenty", "0", "43", "-5", "20weeks", ""])
    def test_reprompts_on_invalid(self, answer):
        harness = _after("Hi", "yes", "Akinyi", answer)

        assert harness.output == GA_RETRY_MSG
        assert harness.participant_data["registration_complete"] is False
        assert "gestational_age_at_enrollment" not in harness.participant_data


def _expected_context(gestational_age, language):
    """Mirror of AIEngine._build_context for a SAFE (non-danger) message."""
    parts = []
    if gestational_age is not None:
        parts.append(f"User's current gestational age: {gestational_age} weeks.")
        for (start, end), guidance in GESTATIONAL_GUIDANCE.items():
            if start <= gestational_age <= end:
                parts.append(f"Trimester guidance: {guidance}")
                break
    if language == "sw":
        parts.append("User prefers Swahili. Respond in Swahili.")
    return "\n".join(parts) if parts else "No additional context available."


class TestRegistered:
    def test_passes_message_through_to_llm(self):
        harness = _run("What should I eat?", REGISTERED)

        assert harness.output == "What should I eat?"
        assert harness.temp_state["registration_route"] == "REGISTERED"
        assert harness.message_tags == []
        assert harness.participant_data == REGISTERED

    def test_context_uses_current_gestational_age(self):
        # Enrolled at 20 weeks 10 days ago -> 21 weeks (whole weeks, as in User.current_gestational_age).
        harness = _run("hello", REGISTERED)
        assert harness.temp_state["llm_context"] == _expected_context(21, "en")
        assert "Second trimester" in harness.temp_state["llm_context"]

    def test_context_in_swahili(self):
        harness = _run("habari", REGISTERED | {"language_preference": "sw"})
        assert harness.temp_state["llm_context"] == _expected_context(21, "sw")

    @pytest.mark.parametrize(("enrolment_weeks", "current"), [(1, 2), (12, 13), (26, 27), (40, 41)])
    def test_trimester_boundaries(self, enrolment_weeks, current):
        harness = _run("hello", REGISTERED | {"gestational_age_at_enrollment": enrolment_weeks})
        assert harness.temp_state["llm_context"] == _expected_context(current, "en")

    def test_no_context_without_gestational_age(self):
        data = {k: v for k, v in REGISTERED.items() if k != "gestational_age_at_enrollment"}
        harness = _run("hello", data)
        assert harness.temp_state["llm_context"] == "No additional context available."
