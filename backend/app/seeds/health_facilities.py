"""Seed data for health facilities in Migori County."""

from app.models.health_facility import FacilityLevel, FacilityType

# Initial health facilities for Migori County, Kenya
MIGORI_FACILITIES = [
    {
        "name": "Migori County Referral Hospital",
        "facility_type": FacilityType.HOSPITAL,
        "facility_level": FacilityLevel.LEVEL_4,
        "phone_number": "0800 723 253",
        "emergency_line": "0800 723 253",
        "county": "Migori",
        "sub_county": "Migori",
        "physical_address": "Migori Town, along Migori-Isebania Road",
        "has_maternity_services": True,
        "has_emergency_services": True,
        "has_24h_services": True,
        "has_ambulance": True,
        "is_active": True,
        "is_verified": True,
        "display_priority": 1,
        "notes": "Main county referral hospital with comprehensive maternal health services including NICU and theater.",
    },
    {
        "name": "Ombo Mission Hospital",
        "facility_type": FacilityType.HOSPITAL,
        "facility_level": FacilityLevel.LEVEL_3,
        "phone_number": "0722 123 456",
        "county": "Migori",
        "sub_county": "Rongo",
        "ward": "East Kamagambo",
        "physical_address": "Ombo, Rongo Sub-County",
        "has_maternity_services": True,
        "has_emergency_services": True,
        "has_24h_services": True,
        "has_ambulance": True,
        "is_active": True,
        "is_verified": True,
        "display_priority": 2,
        "notes": "Faith-based hospital providing comprehensive maternal and child health services.",
    },
    {
        "name": "Isebania Sub-County Hospital",
        "facility_type": FacilityType.HOSPITAL,
        "facility_level": FacilityLevel.LEVEL_3,
        "phone_number": "0733 456 789",
        "county": "Migori",
        "sub_county": "Kuria West",
        "physical_address": "Isebania Town, near Kenya-Tanzania border",
        "has_maternity_services": True,
        "has_emergency_services": True,
        "has_24h_services": True,
        "has_ambulance": False,
        "is_active": True,
        "is_verified": True,
        "display_priority": 3,
        "notes": "Sub-county hospital serving the border region with maternal health services.",
    },
    {
        "name": "Awendo Sub-County Hospital",
        "facility_type": FacilityType.HOSPITAL,
        "facility_level": FacilityLevel.LEVEL_3,
        "phone_number": "0744 567 890",
        "county": "Migori",
        "sub_county": "Awendo",
        "physical_address": "Awendo Town",
        "has_maternity_services": True,
        "has_emergency_services": True,
        "has_24h_services": True,
        "has_ambulance": True,
        "is_active": True,
        "is_verified": True,
        "display_priority": 4,
        "notes": "Sub-county hospital with active maternity wing.",
    },
    {
        "name": "Rongo Sub-County Hospital",
        "facility_type": FacilityType.HOSPITAL,
        "facility_level": FacilityLevel.LEVEL_3,
        "phone_number": "0755 678 901",
        "county": "Migori",
        "sub_county": "Rongo",
        "physical_address": "Rongo Town",
        "has_maternity_services": True,
        "has_emergency_services": True,
        "has_24h_services": False,
        "has_ambulance": False,
        "is_active": True,
        "is_verified": True,
        "display_priority": 5,
        "notes": "Sub-county hospital providing antenatal and delivery services.",
    },
    {
        "name": "Macalder Mission Hospital",
        "facility_type": FacilityType.HOSPITAL,
        "facility_level": FacilityLevel.LEVEL_3,
        "phone_number": "0766 789 012",
        "county": "Migori",
        "sub_county": "Suna West",
        "physical_address": "Macalder, Suna West",
        "has_maternity_services": True,
        "has_emergency_services": True,
        "has_24h_services": True,
        "has_ambulance": True,
        "is_active": True,
        "is_verified": True,
        "display_priority": 6,
        "notes": "Mission hospital with good maternity services and community outreach.",
    },
    {
        "name": "Kehancha Sub-County Hospital",
        "facility_type": FacilityType.HOSPITAL,
        "facility_level": FacilityLevel.LEVEL_3,
        "phone_number": "0777 890 123",
        "county": "Migori",
        "sub_county": "Kuria East",
        "physical_address": "Kehancha Town",
        "has_maternity_services": True,
        "has_emergency_services": True,
        "has_24h_services": False,
        "has_ambulance": False,
        "is_active": True,
        "is_verified": True,
        "display_priority": 7,
        "notes": "Sub-county hospital serving Kuria East with basic emergency obstetric care.",
    },
]


async def seed_health_facilities(db):
    """
    Seed the database with initial health facility data.

    Args:
        db: AsyncSession database connection.
    """
    from app.models.health_facility import HealthFacility
    from sqlalchemy import select

    for facility_data in MIGORI_FACILITIES:
        # Check if facility already exists by name and county
        result = await db.execute(
            select(HealthFacility).where(
                HealthFacility.name == facility_data["name"],
                HealthFacility.county == facility_data["county"],
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  ✓ Facility already exists: {facility_data['name']}")
            continue

        facility = HealthFacility(**facility_data)
        db.add(facility)
        print(f"  + Created facility: {facility_data['name']}")

    await db.commit()
    print(f"\n✓ Seeded {len(MIGORI_FACILITIES)} health facilities for Migori County")
