"""
Open Chat Studio Python node: deterministic obstetric danger-sign gate.

Source of truth for the first node after Start in the Zeya pipeline. Do not edit
this node in the OCS UI; change this file, run ``make test-ocs`` and redeploy
(see docs/ocs-migration.md).

The patterns are verbatim copies of DANGER_SIGN_PATTERNS in
backend/app/services/danger_signs.py, enforced by ocs/tests/test_danger_gate_parity.py.
They live inside ``main`` because OCS executes node code with separate locals, so
module-level names are not visible to ``main``.

Outputs (temp state):
    danger_route: "EMERGENCY" or "SAFE", read by the Static Router that follows.
    danger_categories: matched categories, in detection order.
    danger_keywords: the matched text, one per category.
Returns the user's message unchanged so the SAFE branch receives it.
"""


def main(input: str, **kwargs) -> str:
    import re

    # Danger sign keyword patterns grouped by category.
    # Each pattern is compiled as case-insensitive regex.
    danger_sign_patterns = [
        ("bleeding", [
            re.compile(r"\b(heavy\s+)?bleeding\b", re.IGNORECASE),
            re.compile(r"\bexcessive\s+blood\b", re.IGNORECASE),
            re.compile(r"\bblood\s+(clots?|loss)\b", re.IGNORECASE),
            re.compile(r"\bkutoka\s+damu\b", re.IGNORECASE),  # Swahili: bleeding
            re.compile(r"\bdamu\s+nyingi\b", re.IGNORECASE),  # Swahili: heavy blood
        ]),
        ("headache_vision", [
            re.compile(r"\bsevere\s+headache\b", re.IGNORECASE),
            re.compile(r"\bblurred?\s+vision\b", re.IGNORECASE),
            re.compile(r"\bvision\s+(is\s+)?blurred?\b", re.IGNORECASE),
            re.compile(r"\bseeing\s+(spots?|stars?)\b", re.IGNORECASE),
            re.compile(r"\bkichwa\s+kuuma\b", re.IGNORECASE),  # Swahili: headache
            re.compile(r"\bmacho\s+kuona\s+vibaya\b", re.IGNORECASE),  # Swahili: blurred vision
        ]),
        ("fever", [
            re.compile(r"\bhigh\s+fever\b", re.IGNORECASE),
            re.compile(r"\bsevere\s+fever\b", re.IGNORECASE),
            re.compile(r"\bchills\b", re.IGNORECASE),
            re.compile(r"\bhoma\s+kali\b", re.IGNORECASE),  # Swahili: high fever
            re.compile(r"\bbaridi\s+mwilini\b", re.IGNORECASE),  # Swahili: chills
        ]),
        ("fetal_movement", [
            re.compile(r"\breduced\s+fetal\s+movement\b", re.IGNORECASE),
            re.compile(r"\bno\s+(fetal\s+)?movement\b", re.IGNORECASE),
            re.compile(r"\bbaby\s+(not\s+moving|stopped?\s+moving|isn'?t\s+moving)\b", re.IGNORECASE),
            re.compile(r"\bcan'?t\s+feel\s+(the\s+)?baby\b", re.IGNORECASE),
            re.compile(r"\bmtoto\s+ha(tembei|chezi)\b", re.IGNORECASE),  # Swahili: baby not moving
        ]),
        ("abdominal_pain", [
            re.compile(r"\bsevere\s+(abdominal\s+)?pain\b", re.IGNORECASE),
            re.compile(r"\bstomach\s+pain\b", re.IGNORECASE),
            re.compile(r"\bsharp\s+pain\b", re.IGNORECASE),
            re.compile(r"\btumbo\s+kuuma\s+sana\b", re.IGNORECASE),  # Swahili: severe stomach pain
        ]),
        ("water_breaking", [
            re.compile(r"\bwater\s+(break(ing|s)?|broke)\b", re.IGNORECASE),
            re.compile(r"\bfluid\s+(leaking|leakage|gushing)\b", re.IGNORECASE),
            re.compile(r"\bleaking\s+fluid\b", re.IGNORECASE),
            re.compile(r"\bmaji\s+ya(mekatika|kutoka)\b", re.IGNORECASE),  # Swahili: water breaking
        ]),
        ("convulsions", [
            re.compile(r"\bconvulsion\b", re.IGNORECASE),
            re.compile(r"\bseizure\b", re.IGNORECASE),
            re.compile(r"\bloss\s+of\s+consciousness\b", re.IGNORECASE),
            re.compile(r"\bfaint(ed|ing)\b", re.IGNORECASE),
            re.compile(r"\bpassed?\s+out\b", re.IGNORECASE),
            re.compile(r"\bdegedege\b", re.IGNORECASE),  # Swahili: convulsions
            re.compile(r"\bkupoteza\s+fahamu\b", re.IGNORECASE),  # Swahili: loss of consciousness
        ]),
        ("swelling", [
            re.compile(r"\bsevere\s+swelling\b", re.IGNORECASE),
            re.compile(r"\bswollen\s+(face|hands?|feet)\b", re.IGNORECASE),
            re.compile(r"\bkuvimba\s+sana\b", re.IGNORECASE),  # Swahili: severe swelling
        ]),
    ]

    categories_found = []
    keywords_found = []

    for category, patterns in danger_sign_patterns:
        for pattern in patterns:
            match = pattern.search(input)
            if match:
                if category not in categories_found:
                    categories_found.append(category)
                keywords_found.append(match.group())
                break  # One match per category is sufficient

    set_temp_state_key("danger_route", "EMERGENCY" if categories_found else "SAFE")
    set_temp_state_key("danger_categories", categories_found)
    set_temp_state_key("danger_keywords", keywords_found)

    # Tags carry the detection into the OCS transcript export (see ocs/export_adapter.py).
    # OCS tag names are limited to 100 characters.
    # Keyword tags carry the category because OCS exports tags in alphabetical order.
    for category in categories_found:
        add_message_tag("danger_sign:" + category)
    for index in range(len(keywords_found)):
        keyword = " ".join(keywords_found[index].split())
        add_message_tag(("danger_keyword:" + categories_found[index] + ":" + keyword)[:100])

    return input
