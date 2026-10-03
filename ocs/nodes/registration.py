"""
Open Chat Studio Python node: study registration and LLM context.

Runs on the SAFE branch, after the danger gate, so registration messages are
also checked for danger signs.

Ports ConversationHandler._handle_registration (consent -> name -> gestational
age) and AIEngine._build_context from the Zeya backend, using participant data in
place of the User table. Reply wording is unchanged.

Outputs (temp state):
    registration_route: "REPLY" (return this node's text to the user) or
        "REGISTERED" (continue to the LLM with the user's message).
    llm_context: context block for the LLM system prompt (REGISTERED only).

Registration replies are tagged "registration", and the first-contact turn also
"registration:first_contact". Zeya never logged its registration replies or the
first message, so ocs/export_adapter.py uses these tags to leave them out.
"""


def main(input: str, **kwargs) -> str:
    welcome_en = (
        "Welcome to the Antenatal Education Chatbot! I am here to help you with "
        "information about your pregnancy journey.\n\n"
        "This is a research study chatbot that provides educational information about "
        "maternal health based on WHO and Kenya Ministry of Health guidelines.\n\n"
        "Important: This is educational information, not medical diagnosis. Always "
        "consult your healthcare provider for medical advice.\n\n"
        "Do you consent to participate in this study and receive antenatal education "
        "messages? Please reply YES or NO."
    )
    welcome_sw = (
        "Karibu kwenye Chatbot ya Elimu ya Ujauzito! Niko hapa kukusaidia na "
        "habari kuhusu safari yako ya ujauzito.\n\n"
        "Hii ni chatbot ya utafiti inayotoa habari za kielimu kuhusu afya ya mama "
        "kulingana na miongozo ya WHO na Wizara ya Afya ya Kenya.\n\n"
        "Muhimu: Hii ni habari ya kielimu, si utambuzi wa kimatibabu. Daima "
        "wasiliana na mtoa huduma wako wa afya kwa ushauri wa kimatibabu.\n\n"
        "Je, unakubali kushiriki katika utafiti huu na kupokea ujumbe wa elimu ya "
        "ujauzito? Tafadhali jibu NDIYO au HAPANA."
    )
    gestational_guidance = [
        (
            1,
            12,
            "First trimester: Focus on nutrition (folate, iron), managing morning sickness, "
            "first ANC visit importance, and avoiding harmful substances.",
        ),
        (
            13,
            26,
            "Second trimester: Focus on balanced diet, fetal movement awareness, "
            "anomaly screening, dental care, and preparing for birth.",
        ),
        (
            27,
            40,
            "Third trimester: Focus on birth preparedness, recognizing labor signs, "
            "danger signs awareness, breastfeeding preparation, and newborn care.",
        ),
    ]

    data = get_participant_data() or {}
    now = datetime.datetime.now(datetime.timezone.utc)
    text = input or ""
    text_lower = text.strip().lower()

    def reply(message):
        set_temp_state_key("registration_route", "REPLY")
        add_message_tag("registration")
        return message

    if data.get("registration_complete"):
        gestational_age = None
        if data.get("gestational_age_at_enrollment") is not None:
            enrolled_at = datetime.datetime.fromisoformat(data["enrolled_at"])
            weeks_since_enrollment = (now - enrolled_at).days // 7
            gestational_age = data["gestational_age_at_enrollment"] + weeks_since_enrollment

        parts = []
        if gestational_age is not None:
            parts.append("User's current gestational age: " + str(gestational_age) + " weeks.")
            for guidance in gestational_guidance:
                if guidance[0] <= gestational_age <= guidance[1]:
                    parts.append("Trimester guidance: " + guidance[2])
                    break
        if data.get("language_preference") == "sw":
            parts.append("User prefers Swahili. Respond in Swahili.")

        set_temp_state_key("llm_context", "\n".join(parts) if parts else "No additional context available.")
        set_temp_state_key("registration_route", "REGISTERED")
        return input

    if not data.get("welcome_sent"):
        # First contact: enrol and send the consent request. Zeya ignored the content
        # of this first message.
        language = data.get("language_preference") or "en"
        set_participant_data_key("welcome_sent", True)
        set_participant_data_key("enrolled_at", now.isoformat())
        set_participant_data_key("consent_given", False)
        set_participant_data_key("registration_complete", False)
        set_participant_data_key("language_preference", language)
        set_participant_data_key("study_group", data.get("study_group") or "intervention")
        message = reply(welcome_sw if language == "sw" else welcome_en)
        add_message_tag("registration:first_contact")
        return message

    if not data.get("consent_given"):
        if text_lower in ("yes", "ndiyo", "ndio"):
            set_participant_data_key("consent_given", True)
            set_participant_data_key("consent_given_at", now.isoformat())
            return reply("Thank you for consenting to participate! What is your name?")
        if text_lower in ("no", "hapana"):
            # Zeya deactivated the user here. We record the decision instead, so a later
            # YES re-enrols them, as the reply promises.
            set_participant_data_key("consent_declined", True)
            return reply(
                "Thank you for your response. You can message us anytime if you change your mind. Take care, Mama!"
            )
        return reply("Please reply YES or NO to consent to participate in the study.")

    # OCS merges participant.name into participant data as "name", so a name may already
    # be present (e.g. from the channel). Track this step separately.
    if not data.get("name_collected"):
        name = text.strip()
        set_participant_data_key("name", name)
        set_participant_data_key("name_collected", True)
        return reply(
            "Nice to meet you, " + name + "! "
            "How many weeks pregnant are you? "
            "Please reply with a number (for example: 20)."
        )

    if data.get("gestational_age_at_enrollment") is None:
        weeks = None
        try:
            weeks = int(text_lower.strip().split()[0])
        except (ValueError, IndexError):
            weeks = None
        if weeks is None or weeks < 1 or weeks > 42:
            return reply("Please enter a valid number of weeks (between 1 and 42). For example: 20")

        expected_delivery_date = now.date() + datetime.timedelta(weeks=40 - weeks)
        set_participant_data_key("gestational_age_at_enrollment", weeks)
        set_participant_data_key("expected_delivery_date", expected_delivery_date.isoformat())
        set_participant_data_key("registration_complete", True)
        return reply(
            "You are registered! You are " + str(weeks) + " weeks pregnant. "
            "Your expected delivery date is approximately " + expected_delivery_date.strftime("%B %d, %Y") + ".\n\n"
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

    # Consent, name and gestational age are all set but registration_complete is not
    # (for example, data imported by hand). Finish registration.
    set_participant_data_key("registration_complete", True)
    return reply("Just type your question and I will do my best to help you, Mama!")
