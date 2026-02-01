"""
Unit tests for danger sign detection service.

Tests cover all danger sign categories with both English and Swahili keywords,
as well as negative cases to prevent false positives.
"""

import pytest

from app.services.danger_signs import (
    detect_danger_signs,
    get_emergency_response,
)


class TestDangerSignDetection:
    """Tests for the detect_danger_signs function."""

    # --- Bleeding ---
    @pytest.mark.parametrize(
        "message",
        [
            "I am having heavy bleeding",
            "There is excessive blood",
            "I see blood clots",
            "Ninatoka damu nyingi",
            "bleeding from down there",
        ],
    )
    def test_detects_bleeding(self, message):
        result = detect_danger_signs(message)
        assert result.detected is True
        assert "bleeding" in result.categories

    # --- Headache / Vision ---
    @pytest.mark.parametrize(
        "message",
        [
            "I have a severe headache",
            "My vision is blurred",
            "I am seeing spots",
            "blurred vision since morning",
        ],
    )
    def test_detects_headache_vision(self, message):
        result = detect_danger_signs(message)
        assert result.detected is True
        assert "headache_vision" in result.categories

    # --- Fever ---
    @pytest.mark.parametrize(
        "message",
        [
            "I have high fever",
            "severe fever and chills",
            "having chills all day",
            "nina homa kali",
        ],
    )
    def test_detects_fever(self, message):
        result = detect_danger_signs(message)
        assert result.detected is True
        assert "fever" in result.categories

    # --- Fetal movement ---
    @pytest.mark.parametrize(
        "message",
        [
            "reduced fetal movement",
            "no movement for hours",
            "baby not moving",
            "baby stopped moving",
            "I can't feel the baby",
            "baby isn't moving today",
        ],
    )
    def test_detects_fetal_movement(self, message):
        result = detect_danger_signs(message)
        assert result.detected is True
        assert "fetal_movement" in result.categories

    # --- Abdominal pain ---
    @pytest.mark.parametrize(
        "message",
        [
            "severe abdominal pain",
            "sharp pain in my belly",
            "severe pain that won't stop",
            "stomach pain very bad",
        ],
    )
    def test_detects_abdominal_pain(self, message):
        result = detect_danger_signs(message)
        assert result.detected is True
        assert "abdominal_pain" in result.categories

    # --- Water breaking ---
    @pytest.mark.parametrize(
        "message",
        [
            "my water broke",
            "water breaking right now",
            "fluid leaking from me",
            "leaking fluid down there",
        ],
    )
    def test_detects_water_breaking(self, message):
        result = detect_danger_signs(message)
        assert result.detected is True
        assert "water_breaking" in result.categories

    # --- Convulsions ---
    @pytest.mark.parametrize(
        "message",
        [
            "I had a convulsion",
            "I had a seizure",
            "loss of consciousness",
            "I fainted today",
            "she passed out",
        ],
    )
    def test_detects_convulsions(self, message):
        result = detect_danger_signs(message)
        assert result.detected is True
        assert "convulsions" in result.categories

    # --- Swelling ---
    @pytest.mark.parametrize(
        "message",
        [
            "severe swelling in my face",
            "swollen hands and feet",
        ],
    )
    def test_detects_swelling(self, message):
        result = detect_danger_signs(message)
        assert result.detected is True
        assert "swelling" in result.categories

    # --- Multiple danger signs ---
    def test_detects_multiple_danger_signs(self):
        result = detect_danger_signs(
            "I have severe headache and heavy bleeding and I fainted"
        )
        assert result.detected is True
        assert len(result.categories) >= 2

    # --- No danger signs ---
    @pytest.mark.parametrize(
        "message",
        [
            "What should I eat during pregnancy?",
            "When is my next appointment?",
            "How do I prepare for birth?",
            "My back aches a little",
            "I feel tired today",
            "Hello",
            "Thank you for the information",
        ],
    )
    def test_no_false_positives(self, message):
        result = detect_danger_signs(message)
        assert result.detected is False
        assert len(result.categories) == 0
        assert len(result.keywords) == 0

    # --- Bool behavior ---
    def test_result_bool_true(self):
        result = detect_danger_signs("heavy bleeding")
        assert bool(result) is True

    def test_result_bool_false(self):
        result = detect_danger_signs("hello")
        assert bool(result) is False


class TestEmergencyResponse:
    """Tests for get_emergency_response function."""

    def test_english_response(self):
        response = get_emergency_response("en")
        assert "URGENT" in response
        assert "Migori County Referral Hospital" in response
        assert "educational information" in response

    def test_swahili_response(self):
        response = get_emergency_response("sw")
        assert "DHARURA" in response
        assert "Kaunti ya Migori" in response

    def test_default_is_english(self):
        response = get_emergency_response()
        assert "URGENT" in response
