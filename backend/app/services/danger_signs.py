"""
Danger sign detection service for maternal health emergencies.

Detects keywords and phrases that indicate obstetric danger signs requiring
immediate medical attention, per WHO and Kenya MOH guidelines.
"""

import logging
import re
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Danger sign keyword patterns grouped by category.
# Each pattern is compiled as case-insensitive regex.
DANGER_SIGN_PATTERNS: dict[str, list[re.Pattern]] = {
    "bleeding": [
        re.compile(r"\b(heavy\s+)?bleeding\b", re.IGNORECASE),
        re.compile(r"\bexcessive\s+blood\b", re.IGNORECASE),
        re.compile(r"\bblood\s+(clots?|loss)\b", re.IGNORECASE),
        re.compile(r"\bkutoka\s+damu\b", re.IGNORECASE),  # Swahili: bleeding
        re.compile(r"\bdamu\s+nyingi\b", re.IGNORECASE),  # Swahili: heavy blood
    ],
    "headache_vision": [
        re.compile(r"\bsevere\s+headache\b", re.IGNORECASE),
        re.compile(r"\bblurred?\s+vision\b", re.IGNORECASE),
        re.compile(r"\bvision\s+(is\s+)?blurred?\b", re.IGNORECASE),
        re.compile(r"\bseeing\s+(spots?|stars?)\b", re.IGNORECASE),
        re.compile(r"\bkichwa\s+kuuma\b", re.IGNORECASE),  # Swahili: headache
        re.compile(r"\bmacho\s+kuona\s+vibaya\b", re.IGNORECASE),  # Swahili: blurred vision
    ],
    "fever": [
        re.compile(r"\bhigh\s+fever\b", re.IGNORECASE),
        re.compile(r"\bsevere\s+fever\b", re.IGNORECASE),
        re.compile(r"\bchills\b", re.IGNORECASE),
        re.compile(r"\bhoma\s+kali\b", re.IGNORECASE),  # Swahili: high fever
        re.compile(r"\bbaridi\s+mwilini\b", re.IGNORECASE),  # Swahili: chills
    ],
    "fetal_movement": [
        re.compile(r"\breduced\s+fetal\s+movement\b", re.IGNORECASE),
        re.compile(r"\bno\s+(fetal\s+)?movement\b", re.IGNORECASE),
        re.compile(r"\bbaby\s+(not\s+moving|stopped?\s+moving|isn'?t\s+moving)\b", re.IGNORECASE),
        re.compile(r"\bcan'?t\s+feel\s+(the\s+)?baby\b", re.IGNORECASE),
        re.compile(r"\bmtoto\s+ha(tembei|chezi)\b", re.IGNORECASE),  # Swahili: baby not moving
    ],
    "abdominal_pain": [
        re.compile(r"\bsevere\s+(abdominal\s+)?pain\b", re.IGNORECASE),
        re.compile(r"\bstomach\s+pain\b", re.IGNORECASE),
        re.compile(r"\bsharp\s+pain\b", re.IGNORECASE),
        re.compile(r"\btumbo\s+kuuma\s+sana\b", re.IGNORECASE),  # Swahili: severe stomach pain
    ],
    "water_breaking": [
        re.compile(r"\bwater\s+(break(ing|s)?|broke)\b", re.IGNORECASE),
        re.compile(r"\bfluid\s+(leaking|leakage|gushing)\b", re.IGNORECASE),
        re.compile(r"\bleaking\s+fluid\b", re.IGNORECASE),
        re.compile(r"\bmaji\s+ya(mekatika|kutoka)\b", re.IGNORECASE),  # Swahili: water breaking
    ],
    "convulsions": [
        re.compile(r"\bconvulsion\b", re.IGNORECASE),
        re.compile(r"\bseizure\b", re.IGNORECASE),
        re.compile(r"\bloss\s+of\s+consciousness\b", re.IGNORECASE),
        re.compile(r"\bfaint(ed|ing)\b", re.IGNORECASE),
        re.compile(r"\bpassed?\s+out\b", re.IGNORECASE),
        re.compile(r"\bdegedege\b", re.IGNORECASE),  # Swahili: convulsions
        re.compile(r"\bkupoteza\s+fahamu\b", re.IGNORECASE),  # Swahili: loss of consciousness
    ],
    "swelling": [
        re.compile(r"\bsevere\s+swelling\b", re.IGNORECASE),
        re.compile(r"\bswollen\s+(face|hands?|feet)\b", re.IGNORECASE),
        re.compile(r"\bkuvimba\s+sana\b", re.IGNORECASE),  # Swahili: severe swelling
    ],
}

# Emergency response templates (without hardcoded facilities)
EMERGENCY_RESPONSE_HEADER_EN = (
    "URGENT: This sounds like it could be a danger sign that requires immediate "
    "medical attention. Please do the following right away:\n\n"
    "1. Go to your nearest health facility immediately or call emergency services.\n"
    "2. If you cannot travel, ask someone nearby to help you get to the hospital.\n"
    "3. Do NOT wait to see if symptoms improve on their own.\n\n"
)

EMERGENCY_RESPONSE_HEADER_SW = (
    "DHARURA: Hii inaonekana kama dalili ya hatari inayohitaji matibabu ya haraka. "
    "Tafadhali fanya yafuatayo mara moja:\n\n"
    "1. Nenda hospitali iliyo karibu nawe mara moja au piga simu ya dharura.\n"
    "2. Ikiwa huwezi kusafiri, mwombe mtu aliye karibu akusaidie kwenda hospitalini.\n"
    "3. USISUBIRI kuona kama dalili zitaboreshwa zenyewe.\n\n"
)

EMERGENCY_RESPONSE_FOOTER_EN = (
    "\n\nThis is educational information, not medical diagnosis. "
    "Always consult your healthcare provider for medical advice."
)

EMERGENCY_RESPONSE_FOOTER_SW = (
    "\n\nHii ni taarifa ya kielimu, si utambuzi wa kimatibabu. "
    "Daima wasiliana na mtoa huduma wako wa afya kwa ushauri wa kimatibabu."
)

# Fallback emergency contacts (used only if database is unavailable)
FALLBACK_CONTACTS_EN = (
    "Nearest facilities in Migori County:\n"
    "- Migori County Referral Hospital: 0800 723 253\n"
    "- Ombo Mission Hospital\n"
    "- Isebania Sub-County Hospital"
)

FALLBACK_CONTACTS_SW = (
    "Hospitali za karibu katika Kaunti ya Migori:\n"
    "- Hospitali ya Rufaa ya Kaunti ya Migori: 0800 723 253\n"
    "- Hospitali ya Ombo Mission\n"
    "- Hospitali ya Isebania Sub-County"
)


class DangerSignResult:
    """Result of danger sign detection."""

    def __init__(self, detected: bool, categories: list[str], keywords: list[str]):
        self.detected = detected
        self.categories = categories
        self.keywords = keywords

    def __bool__(self) -> bool:
        return self.detected


def detect_danger_signs(message: str) -> DangerSignResult:
    """
    Scan a message for danger sign keywords.

    Returns a DangerSignResult with detection status, matched categories,
    and the specific keywords found.
    """
    categories_found: list[str] = []
    keywords_found: list[str] = []

    for category, patterns in DANGER_SIGN_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(message)
            if match:
                if category not in categories_found:
                    categories_found.append(category)
                keywords_found.append(match.group())
                break  # One match per category is sufficient

    return DangerSignResult(
        detected=len(categories_found) > 0,
        categories=categories_found,
        keywords=keywords_found,
    )


async def get_emergency_response(
    db: Optional[AsyncSession] = None,
    county: str = "Migori",
    language: str = "en",
) -> str:
    """
    Get the localized emergency response message with facility contacts.

    Args:
        db: Database session (optional). If None, uses fallback contacts.
        county: County name for facility lookup.
        language: Response language ("en" or "sw").

    Returns:
        Formatted emergency response message with facility contacts.
    """
    from app.services.health_facility_service import health_facility_service

    # Build header
    header = (
        EMERGENCY_RESPONSE_HEADER_SW if language == "sw" else EMERGENCY_RESPONSE_HEADER_EN
    )

    # Get facility contacts
    facilities_text = ""
    if db is not None:
        try:
            facilities = await health_facility_service.get_emergency_facilities(
                db, county=county, limit=5
            )
            if facilities:
                facilities_text = health_facility_service.format_emergency_message(
                    facilities, language=language
                )
            else:
                # No facilities found in database, use fallback
                logger.warning(
                    "No emergency facilities found for county: %s, using fallback",
                    county,
                )
                facilities_text = (
                    FALLBACK_CONTACTS_SW if language == "sw" else FALLBACK_CONTACTS_EN
                )
        except Exception as e:
            logger.error(
                "Failed to fetch emergency facilities: %s, using fallback", str(e)
            )
            facilities_text = (
                FALLBACK_CONTACTS_SW if language == "sw" else FALLBACK_CONTACTS_EN
            )
    else:
        # No database session provided, use fallback
        facilities_text = (
            FALLBACK_CONTACTS_SW if language == "sw" else FALLBACK_CONTACTS_EN
        )

    # Build footer
    footer = (
        EMERGENCY_RESPONSE_FOOTER_SW if language == "sw" else EMERGENCY_RESPONSE_FOOTER_EN
    )

    return header + facilities_text + footer


def get_emergency_response_sync(language: str = "en") -> str:
    """
    Get emergency response message without database access (fallback).

    DEPRECATED: Use get_emergency_response() instead with database session.
    This function is kept for backward compatibility only.
    """
    header = (
        EMERGENCY_RESPONSE_HEADER_SW if language == "sw" else EMERGENCY_RESPONSE_HEADER_EN
    )
    contacts = FALLBACK_CONTACTS_SW if language == "sw" else FALLBACK_CONTACTS_EN
    footer = (
        EMERGENCY_RESPONSE_FOOTER_SW if language == "sw" else EMERGENCY_RESPONSE_FOOTER_EN
    )
    return header + contacts + footer
