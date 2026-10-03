"""
Build an Open Chat Studio participant import CSV from Zeya's users table.

Imported participants carry their consent, name, gestational age, language and
study group, so enrolled women go straight to the chatbot without registering again.

    \\copy (SELECT id, whatsapp_id, name, consent_given, consent_given_at,
            gestational_age_at_enrollment, expected_delivery_date, enrolled_at,
            registration_complete, language_preference, study_group, is_active
            FROM users) TO 'zeya_users_full.csv' CSV HEADER

    python -m ocs.seed_participants --zeya-users zeya_users_full.csv --out ocs_participants.csv

Then import ocs_participants.csv on the chatbot's Participants page in OCS.

Users that an admin deactivated after they consented are left out and listed on
stderr: Zeya ignored their messages, and they must not start getting replies
without a decision from the study team.
"""

import argparse
import csv
import json
import sys
from datetime import datetime

OCS_COLUMNS = [
    "identifier",
    "channel",
    "name",
    "data.welcome_sent",
    "data.consent_given",
    "data.consent_declined",
    "data.consent_given_at",
    "data.name_collected",
    "data.gestational_age_at_enrollment",
    "data.expected_delivery_date",
    "data.enrolled_at",
    "data.registration_complete",
    "data.language_preference",
    "data.study_group",
    "data.zeya_user_id",
]


def _bool(value: str) -> bool:
    return str(value).strip().lower() in {"t", "true", "1", "yes"}


def _iso_datetime(value: str) -> str | None:
    return datetime.fromisoformat(value).isoformat() if value else None


def zeya_user_to_participant(user: dict) -> dict:
    """Map one row of the Zeya users table to one OCS import row."""
    consent_given = _bool(user["consent_given"])
    name = (user.get("name") or "").strip()
    weeks = user.get("gestational_age_at_enrollment")
    data = {
        "welcome_sent": True,
        "consent_given": consent_given,
        "consent_declined": True if not consent_given and not _bool(user["is_active"]) else None,
        "consent_given_at": _iso_datetime(user.get("consent_given_at")),
        "name_collected": True if name else None,
        "gestational_age_at_enrollment": int(weeks) if weeks else None,
        "expected_delivery_date": user.get("expected_delivery_date") or None,
        "enrolled_at": _iso_datetime(user.get("enrolled_at")),
        "registration_complete": _bool(user["registration_complete"]),
        "language_preference": user.get("language_preference") or "en",
        "study_group": user.get("study_group") or "intervention",
        "zeya_user_id": user["id"],
    }
    row = {"identifier": user["whatsapp_id"], "channel": "whatsapp", "name": name}
    for key, value in data.items():
        # OCS parses each data.* cell as JSON and skips empty cells.
        row[f"data.{key}"] = "" if value is None else json.dumps(value)
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--zeya-users", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    with open(args.zeya_users, newline="", encoding="utf-8") as f:
        users = list(csv.DictReader(f))

    rows, skipped = [], []
    for user in users:
        if _bool(user["consent_given"]) and not _bool(user["is_active"]):
            skipped.append(user["whatsapp_id"])
            continue
        rows.append(zeya_user_to_participant(user))

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OCS_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} participants to {args.out}", file=sys.stderr)
    if skipped:
        print(f"Skipped {len(skipped)} deactivated consented users: {', '.join(skipped)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
