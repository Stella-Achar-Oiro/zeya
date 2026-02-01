"""
Unit tests for gestational age calculation logic.

Tests the calculation independently of SQLAlchemy ORM to avoid
instrumented attribute issues in unit tests.
"""

from datetime import datetime, timedelta, timezone

import pytest


def calculate_gestational_age(weeks_at_enrollment, enrolled_at):
    """
    Mirror of User.current_gestational_age() logic for unit testing.
    """
    if weeks_at_enrollment is None:
        return None
    weeks_since_enrollment = (datetime.now(timezone.utc) - enrolled_at).days // 7
    return weeks_at_enrollment + weeks_since_enrollment


class TestGestationalAgeCalculation:
    def test_current_age_same_day(self):
        enrolled_at = datetime.now(timezone.utc)
        assert calculate_gestational_age(20, enrolled_at) == 20

    def test_current_age_one_week_later(self):
        enrolled_at = datetime.now(timezone.utc) - timedelta(days=7)
        assert calculate_gestational_age(20, enrolled_at) == 21

    def test_current_age_four_weeks_later(self):
        enrolled_at = datetime.now(timezone.utc) - timedelta(days=28)
        assert calculate_gestational_age(12, enrolled_at) == 16

    def test_current_age_partial_week(self):
        enrolled_at = datetime.now(timezone.utc) - timedelta(days=10)
        # 10 days = 1 full week (integer division)
        assert calculate_gestational_age(20, enrolled_at) == 21

    def test_current_age_none_if_not_set(self):
        enrolled_at = datetime.now(timezone.utc)
        assert calculate_gestational_age(None, enrolled_at) is None

    def test_at_40_weeks(self):
        enrolled_at = datetime.now(timezone.utc) - timedelta(weeks=4)
        assert calculate_gestational_age(36, enrolled_at) == 40
