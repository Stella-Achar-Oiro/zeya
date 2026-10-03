"""
Open Chat Studio Python node: emergency response for detected danger signs.

Runs on the EMERGENCY branch of the danger router. There is no LLM on this branch,
so the message never waits on model latency or availability.

The text is the same as backend/app/services/danger_signs.py get_emergency_response():
header, nearest facilities, footer. The facility list is a static copy of the top 5
verified, active, emergency-capable Migori facilities in
backend/app/seeds/health_facilities.py, ordered by display_priority then name.
ocs/tests/test_emergency_response_node.py fails if this copy and the seed differ.

Language comes from participant data ``language_preference``; anything other than
"sw" gets English, as in Zeya.
"""


def main(input: str, **kwargs) -> str:
    header_en = (
        "URGENT: This sounds like it could be a danger sign that requires immediate "
        "medical attention. Please do the following right away:\n\n"
        "1. Go to your nearest health facility immediately or call emergency services.\n"
        "2. If you cannot travel, ask someone nearby to help you get to the hospital.\n"
        "3. Do NOT wait to see if symptoms improve on their own.\n\n"
    )
    header_sw = (
        "DHARURA: Hii inaonekana kama dalili ya hatari inayohitaji matibabu ya haraka. "
        "Tafadhali fanya yafuatayo mara moja:\n\n"
        "1. Nenda hospitali iliyo karibu nawe mara moja au piga simu ya dharura.\n"
        "2. Ikiwa huwezi kusafiri, mwombe mtu aliye karibu akusaidie kwenda hospitalini.\n"
        "3. USISUBIRI kuona kama dalili zitaboreshwa zenyewe.\n\n"
    )
    footer_en = (
        "\n\nThis is educational information, not medical diagnosis. "
        "Always consult your healthcare provider for medical advice."
    )
    footer_sw = (
        "\n\nHii ni taarifa ya kielimu, si utambuzi wa kimatibabu. "
        "Daima wasiliana na mtoa huduma wako wa afya kwa ushauri wa kimatibabu."
    )

    # (name, phone) in display order.
    facilities = [
        ("Migori County Referral Hospital", "0800 723 253"),
        ("Ombo Mission Hospital", "0722 123 456"),
        ("Isebania Sub-County Hospital", "0733 456 789"),
        ("Awendo Sub-County Hospital", "0744 567 890"),
        ("Rongo Sub-County Hospital", "0755 678 901"),
    ]

    # The OCS sandbox does not support tuple-unpacking assignment (no _unpack_sequence_),
    # so each value is assigned separately.
    language = (get_participant_data() or {}).get("language_preference")
    if language == "sw":
        header = header_sw
        facilities_title = "Hospitali za karibu:\n"
        footer = footer_sw
    else:
        header = header_en
        facilities_title = "Nearest facilities:\n"
        footer = footer_en

    facility_lines = ["- " + name + ": " + phone for name, phone in facilities]
    return header + facilities_title + "\n".join(facility_lines) + footer
