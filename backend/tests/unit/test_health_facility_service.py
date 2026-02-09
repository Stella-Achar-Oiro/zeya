"""Unit tests for health facility service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_facility import FacilityLevel, FacilityType, HealthFacility
from app.schemas.health_facility import HealthFacilityCreate, HealthFacilityUpdate
from app.services.health_facility_service import health_facility_service


@pytest.fixture
async def sample_facility_data():
    """Sample health facility data."""
    return HealthFacilityCreate(
        name="Test Hospital",
        facility_type=FacilityType.HOSPITAL,
        facility_level=FacilityLevel.LEVEL_4,
        phone_number="0700123456",
        county="Migori",
        has_maternity_services=True,
        has_emergency_services=True,
        is_verified=True,
        display_priority=1,
    )


@pytest.fixture
async def created_facility(db_session: AsyncSession, sample_facility_data):
    """Create a facility in the database."""
    facility = await health_facility_service.create(db_session, sample_facility_data)
    await db_session.commit()
    return facility


@pytest.mark.asyncio
async def test_create_facility(db_session: AsyncSession, sample_facility_data):
    """Test creating a health facility."""
    facility = await health_facility_service.create(db_session, sample_facility_data)

    assert facility.id is not None
    assert facility.name == "Test Hospital"
    assert facility.facility_type == FacilityType.HOSPITAL
    assert facility.county == "Migori"
    assert facility.is_active is True
    assert facility.is_verified is True


@pytest.mark.asyncio
async def test_get_by_id(db_session: AsyncSession, created_facility):
    """Test getting a facility by ID."""
    facility = await health_facility_service.get_by_id(
        db_session, created_facility.id
    )

    assert facility is not None
    assert facility.id == created_facility.id
    assert facility.name == created_facility.name


@pytest.mark.asyncio
async def test_get_by_county(db_session: AsyncSession, sample_facility_data):
    """Test getting facilities by county."""
    # Create two facilities in the same county
    await health_facility_service.create(db_session, sample_facility_data)

    data2 = sample_facility_data.model_copy()
    data2.name = "Another Hospital"
    await health_facility_service.create(db_session, data2)
    await db_session.commit()

    facilities = await health_facility_service.get_by_county(db_session, "Migori")

    assert len(facilities) == 2
    assert all(f.county == "Migori" for f in facilities)


@pytest.mark.asyncio
async def test_get_emergency_facilities(db_session: AsyncSession, sample_facility_data):
    """Test getting emergency facilities."""
    # Create a verified emergency facility
    await health_facility_service.create(db_session, sample_facility_data)

    # Create an unverified facility (should not appear)
    unverified_data = sample_facility_data.model_copy()
    unverified_data.name = "Unverified Hospital"
    unverified_data.is_verified = False
    await health_facility_service.create(db_session, unverified_data)
    await db_session.commit()

    facilities = await health_facility_service.get_emergency_facilities(
        db_session, "Migori", limit=10
    )

    assert len(facilities) == 1
    assert facilities[0].name == "Test Hospital"
    assert facilities[0].is_verified is True


@pytest.mark.asyncio
async def test_update_facility(db_session: AsyncSession, created_facility):
    """Test updating a facility."""
    update_data = HealthFacilityUpdate(
        phone_number="0711222333", has_ambulance=True
    )

    updated = await health_facility_service.update(
        db_session, created_facility, update_data
    )
    await db_session.commit()

    assert updated.phone_number == "0711222333"
    assert updated.has_ambulance is True
    assert updated.name == created_facility.name  # Unchanged


@pytest.mark.asyncio
async def test_soft_delete(db_session: AsyncSession, created_facility):
    """Test soft deleting a facility."""
    await health_facility_service.delete(db_session, created_facility)
    await db_session.commit()

    # Facility should still exist but be inactive
    facility = await health_facility_service.get_by_id(
        db_session, created_facility.id
    )
    assert facility is not None
    assert facility.is_active is False


@pytest.mark.asyncio
async def test_format_emergency_message(sample_facility_data):
    """Test formatting emergency message."""
    # Create facility object (not in DB)
    facility = HealthFacility(**sample_facility_data.model_dump())

    # Test English
    message_en = health_facility_service.format_emergency_message(
        [facility], language="en"
    )
    assert "Nearest facilities:" in message_en
    assert "Test Hospital" in message_en
    assert "0700123456" in message_en

    # Test Swahili
    message_sw = health_facility_service.format_emergency_message(
        [facility], language="sw"
    )
    assert "Hospitali za karibu:" in message_sw
    assert "Test Hospital" in message_sw


@pytest.mark.asyncio
async def test_display_priority_ordering(db_session: AsyncSession, sample_facility_data):
    """Test that facilities are ordered by display priority."""
    # Create facilities with different priorities
    data1 = sample_facility_data.model_copy()
    data1.name = "Low Priority Hospital"
    data1.display_priority = 100
    await health_facility_service.create(db_session, data1)

    data2 = sample_facility_data.model_copy()
    data2.name = "High Priority Hospital"
    data2.display_priority = 1
    await health_facility_service.create(db_session, data2)

    data3 = sample_facility_data.model_copy()
    data3.name = "Medium Priority Hospital"
    data3.display_priority = 50
    await health_facility_service.create(db_session, data3)
    await db_session.commit()

    facilities = await health_facility_service.get_by_county(db_session, "Migori")

    assert facilities[0].name == "High Priority Hospital"
    assert facilities[1].name == "Medium Priority Hospital"
    assert facilities[2].name == "Low Priority Hospital"
