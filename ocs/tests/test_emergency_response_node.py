"""
The emergency-response node must send exactly what Zeya sends today: the same
header, the same top-5 Migori facilities (from the seed data) formatted the same
way, and the same footer, in English and Swahili. It must not depend on the
database, the network or the message text.
"""

import pytest

from app.models.health_facility import HealthFacility
from app.seeds.health_facilities import MIGORI_FACILITIES
from app.services.danger_signs import (
    EMERGENCY_RESPONSE_FOOTER_EN,
    EMERGENCY_RESPONSE_FOOTER_SW,
    EMERGENCY_RESPONSE_HEADER_EN,
    EMERGENCY_RESPONSE_HEADER_SW,
)
from app.services.health_facility_service import health_facility_service
from ocs.tests.conftest import node_source
from ocs.tests.sandbox import NodeHarness

HEADERS = {"en": EMERGENCY_RESPONSE_HEADER_EN, "sw": EMERGENCY_RESPONSE_HEADER_SW}
FOOTERS = {"en": EMERGENCY_RESPONSE_FOOTER_EN, "sw": EMERGENCY_RESPONSE_FOOTER_SW}


def _seeded_emergency_facilities() -> list[HealthFacility]:
    """Same filter and order as HealthFacilityService.get_emergency_facilities(county="Migori", limit=5)."""
    eligible = [
        HealthFacility(**data)
        for data in MIGORI_FACILITIES
        if data["county"].lower() == "migori"
        and data["is_active"]
        and data["has_emergency_services"]
        and data["is_verified"]
    ]
    return sorted(eligible, key=lambda f: (f.display_priority, f.name))[:5]


def _expected_message(language: str) -> str:
    facilities = health_facility_service.format_emergency_message(_seeded_emergency_facilities(), language=language)
    return HEADERS[language] + facilities + FOOTERS[language]


def _run(participant_data: dict, message: str = "heavy bleeding") -> str:
    return NodeHarness(node_source("emergency_response"), participant_data=participant_data).run(message)


@pytest.mark.parametrize("language", ["en", "sw"])
def test_message_matches_zeya(language):
    assert _run({"language_preference": language}) == _expected_message(language)


@pytest.mark.parametrize("participant_data", [{}, {"language_preference": None}, {"language_preference": "fr"}])
def test_defaults_to_english(participant_data):
    assert _run(participant_data) == _expected_message("en")


def test_lists_five_facilities_with_phone_numbers():
    message = _run({})
    facilities = _seeded_emergency_facilities()
    assert len(facilities) == 5
    for facility in facilities:
        assert f"- {facility.name}: {facility.phone_number}" in message


@pytest.mark.parametrize("message", ["", "mtoto hatembei", "x" * 5000], ids=["empty", "swahili", "long"])
def test_output_does_not_depend_on_message(message):
    assert _run({"language_preference": "sw"}, message) == _expected_message("sw")


def _looks_like_placeholder(phone: str) -> bool:
    """Six-digit ascending runs such as 123 456 or 789 012."""
    digits = [int(c) for c in phone if c.isdigit()][-6:]
    return all((b - a) % 10 == 1 for a, b in zip(digits, digits[1:], strict=False))


@pytest.mark.xfail(
    strict=True,
    reason="GO-LIVE BLOCKER: seed phone numbers for facilities 2-5 look like placeholders. "
    "Verify real numbers with Migori County Health, update app/seeds/health_facilities.py and the "
    "node, then remove this marker.",
)
def test_facility_numbers_are_not_placeholders():
    placeholders = [f.name for f in _seeded_emergency_facilities() if _looks_like_placeholder(f.phone_number)]
    assert placeholders == []
