"""Integration tests for danger sign detection with database facilities."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.health_facility import HealthFacilityCreate
from app.services.danger_signs import detect_danger_signs, get_emergency_response
from app.services.health_facility_service import health_facility_service
from app.models.health_facility import FacilityType, FacilityLevel


@pytest.fixture
async def migori_facilities(db_session: AsyncSession):
    """Create sample facilities in Migori County."""
    facilities_data = [
        HealthFacilityCreate(
            name="Migori County Referral Hospital",
            facility_type=FacilityType.HOSPITAL,
            facility_level=FacilityLevel.LEVEL_4,
            phone_number="0800 723 253",
            county="Migori",
            has_emergency_services=True,
            is_verified=True,
            display_priority=1,
        ),
        HealthFacilityCreate(
            name="Ombo Mission Hospital",
            facility_type=FacilityType.HOSPITAL,
            facility_level=FacilityLevel.LEVEL_3,
            phone_number="0722 123 456",
            county="Migori",
            has_emergency_services=True,
            is_verified=True,
            display_priority=2,
        ),
    ]

    facilities = []
    for data in facilities_data:
        facility = await health_facility_service.create(db_session, data)
        facilities.append(facility)

    await db_session.commit()
    return facilities


@pytest.mark.asyncio
async def test_danger_sign_detection():
    """Test basic danger sign detection still works."""
    # Test bleeding detection
    result = detect_danger_signs("I have severe bleeding")
    assert result.detected is True
    assert "bleeding" in result.categories

    # Test headache detection
    result = detect_danger_signs("I have a severe headache and blurred vision")
    assert result.detected is True
    assert "headache_vision" in result.categories

    # Test normal message
    result = detect_danger_signs("How are you today?")
    assert result.detected is False


@pytest.mark.asyncio
async def test_emergency_response_with_database(
    db_session: AsyncSession, migori_facilities
):
    """Test emergency response generation with database facilities."""
    response_en = await get_emergency_response(
        db=db_session, county="Migori", language="en"
    )

    # Check structure
    assert "URGENT" in response_en
    assert "Nearest facilities:" in response_en
    assert "Migori County Referral Hospital" in response_en
    assert "0800 723 253" in response_en
    assert "educational information" in response_en

    # Check it includes multiple facilities
    assert "Ombo Mission Hospital" in response_en


@pytest.mark.asyncio
async def test_emergency_response_swahili(
    db_session: AsyncSession, migori_facilities
):
    """Test emergency response in Swahili with database facilities."""
    response_sw = await get_emergency_response(
        db=db_session, county="Migori", language="sw"
    )

    # Check Swahili text
    assert "DHARURA" in response_sw
    assert "Hospitali za karibu:" in response_sw
    assert "Migori County Referral Hospital" in response_sw
    assert "taarifa ya kielimu" in response_sw


@pytest.mark.asyncio
async def test_emergency_response_no_database():
    """Test fallback emergency response when no database is provided."""
    response = await get_emergency_response(db=None, county="Migori", language="en")

    # Should use fallback contacts
    assert "URGENT" in response
    assert "Migori County Referral Hospital: 0800 723 253" in response
    assert "educational information" in response


@pytest.mark.asyncio
async def test_emergency_response_no_facilities_found(db_session: AsyncSession):
    """Test emergency response when no facilities found for a county."""
    # Request facilities for a county with no data
    response = await get_emergency_response(
        db=db_session, county="Nairobi", language="en"
    )

    # Should fall back to hardcoded Migori facilities
    assert "URGENT" in response
    assert "Migori County Referral Hospital: 0800 723 253" in response


@pytest.mark.asyncio
async def test_emergency_response_respects_verification(db_session: AsyncSession):
    """Test that only verified facilities appear in emergency response."""
    # Create an unverified facility
    unverified = HealthFacilityCreate(
        name="Unverified Hospital",
        facility_type=FacilityType.HOSPITAL,
        phone_number="0700000000",
        county="Kisumu",
        has_emergency_services=True,
        is_verified=False,  # Not verified
        display_priority=1,
    )
    await health_facility_service.create(db_session, unverified)

    # Create a verified facility
    verified = HealthFacilityCreate(
        name="Verified Hospital",
        facility_type=FacilityType.HOSPITAL,
        phone_number="0711111111",
        county="Kisumu",
        has_emergency_services=True,
        is_verified=True,  # Verified
        display_priority=2,
    )
    await health_facility_service.create(db_session, verified)
    await db_session.commit()

    response = await get_emergency_response(
        db=db_session, county="Kisumu", language="en"
    )

    # Only verified facility should appear
    assert "Verified Hospital" in response
    assert "Unverified Hospital" not in response


@pytest.mark.asyncio
async def test_facility_priority_ordering(db_session: AsyncSession):
    """Test that facilities are ordered by priority in emergency response."""
    # Create facilities with different priorities
    for i, priority in enumerate([50, 10, 100], start=1):
        data = HealthFacilityCreate(
            name=f"Hospital Priority {priority}",
            facility_type=FacilityType.HOSPITAL,
            phone_number=f"070000000{i}",
            county="TestCounty",
            has_emergency_services=True,
            is_verified=True,
            display_priority=priority,
        )
        await health_facility_service.create(db_session, data)

    await db_session.commit()

    response = await get_emergency_response(
        db=db_session, county="TestCounty", language="en"
    )

    # Find positions of hospitals in response
    pos_10 = response.find("Hospital Priority 10")
    pos_50 = response.find("Hospital Priority 50")
    pos_100 = response.find("Hospital Priority 100")

    # Lower priority number should appear first
    assert pos_10 < pos_50 < pos_100
