"""
Convert an Open Chat Studio transcript export into Zeya's conversations_export.csv.

The output has the columns and value formats of
backend/app/services/analytics_service.py export_conversations_csv(), so the
planned analysis can read Zeya-era and OCS-era data the same way.

    python -m ocs.export_adapter \\
        --ocs-export ocs_sessions.csv \\
        --zeya-users zeya_users.csv \\
        --out conversations_export_ocs.csv

``--zeya-users`` links OCS participants to existing Zeya users by WhatsApp id (the
OCS participant identifier) and
keeps Zeya's STUDY_#### numbering. Produce it from the Zeya database with:

    \\copy (SELECT DISTINCT u.id AS user_id, u.whatsapp_id FROM users u
            JOIN conversations c ON c.user_id = u.id) TO 'zeya_users.csv' CSV HEADER

Rules, matching what Zeya logged:
- Participants whose latest participant data does not have consent_given are left out.
- Turns tagged "registration:first_contact" are left out (Zeya did not log the first
  message). On other "registration" turns only the user's message is kept (Zeya
  logged registration answers but not its replies).
- danger_sign and danger_keywords are set on the outgoing row only, from the gate's
  message tags, with keywords in Zeya's category order. Whitespace inside a keyword
  is collapsed to single spaces.
- gestational_age is the participant's gestational age when the message was sent.
- response_time_ms is the outgoing message time minus the incoming message time.
"""

import argparse
import csv
import json
import sys
from collections.abc import Iterable
from datetime import datetime

ZEYA_COLUMNS = [
    "study_id",
    "study_group",
    "direction",
    "message_text",
    "gestational_age",
    "danger_sign",
    "danger_keywords",
    "response_time_ms",
    "timestamp",
]

# DANGER_SIGN_PATTERNS order in backend/app/services/danger_signs.py.
CATEGORY_ORDER = [
    "bleeding",
    "headache_vision",
    "fever",
    "fetal_movement",
    "abdominal_pain",
    "water_breaking",
    "convulsions",
    "swelling",
]

DIRECTIONS = {"human": "incoming", "ai": "outgoing"}


def _digits(phone: str) -> str:
    return "".join(c for c in phone or "" if c.isdigit())


def _participant_data(row: dict) -> dict | None:
    try:
        data = json.loads(row.get("Participant Data") or "")
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _tags(row: dict) -> list[str]:
    return [t for t in (row.get("Message Tags") or "").split(", ") if t]


def _timestamp(row: dict) -> datetime:
    return datetime.fromisoformat(row["Message Date"])


def _gestational_age(data: dict | None, at: datetime) -> int | str:
    """Mirror of User.current_gestational_age() evaluated at the message time."""
    if not data or data.get("gestational_age_at_enrollment") is None or not data.get("enrolled_at"):
        return ""
    enrolled_at = datetime.fromisoformat(data["enrolled_at"])
    return data["gestational_age_at_enrollment"] + (at - enrolled_at).days // 7


def _danger_keywords(tags: list[str]) -> str:
    keywords = []
    for tag in tags:
        if tag.startswith("danger_keyword:"):
            category, _, keyword = tag.removeprefix("danger_keyword:").partition(":")
            order = CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else len(CATEGORY_ORDER)
            keywords.append((order, keyword))
    return ", ".join(keyword for _, keyword in sorted(keywords, key=lambda item: item[0]))


def _consented_participants(rows: list[dict]) -> set[str]:
    latest: dict[str, tuple[datetime, dict]] = {}
    for row in rows:
        data = _participant_data(row)
        if data is None:
            continue
        key = row["Participant Public ID"]
        at = _timestamp(row)
        if key not in latest or at >= latest[key][0]:
            latest[key] = (at, data)
    return {key for key, (_, data) in latest.items() if data.get("consent_given") is True}


def convert_ocs_export(rows: Iterable[dict], wa_id_to_user_id: dict[str, str]) -> list[dict]:
    """Convert OCS export rows to Zeya rows keyed by ``user_key`` instead of ``study_id``.

    ``user_key`` is the linked Zeya user id, or ``ocs:<participant public id>``.
    """
    rows = [r for r in rows if r.get("Message Type") in DIRECTIONS]
    consented = _consented_participants(rows)

    traces: dict[str, list[dict]] = {}
    for row in rows:
        traces.setdefault(row["Trace ID"], []).append(row)

    output = []
    for row in sorted(rows, key=_timestamp):
        if row["Participant Public ID"] not in consented:
            continue
        trace_rows = traces[row["Trace ID"]]
        trace_tags = [tag for r in trace_rows for tag in _tags(r)]
        if "registration:first_contact" in trace_tags:
            continue
        direction = DIRECTIONS[row["Message Type"]]
        tags = _tags(row)
        if direction == "outgoing" and "registration" in tags:
            continue

        data = _participant_data(row)
        at = _timestamp(row)
        is_danger = direction == "outgoing" and any(t.startswith("danger_sign:") for t in tags)
        response_time_ms: int | str = ""
        if direction == "outgoing":
            incoming = [r for r in trace_rows if r["Message Type"] == "human"]
            if incoming:
                response_time_ms = int((at - _timestamp(incoming[0])).total_seconds() * 1000) or ""

        user_id = wa_id_to_user_id.get(_digits(row["Participant Identifier"]))
        output.append(
            {
                "user_key": user_id or f"ocs:{row['Participant Public ID']}",
                "study_group": (data or {}).get("study_group") or "",
                "direction": direction,
                "message_text": row["Message Content"],
                "gestational_age": _gestational_age(data, at),
                "danger_sign": is_danger,
                "danger_keywords": _danger_keywords(tags) if is_danger else "",
                "response_time_ms": response_time_ms,
                "timestamp": at.isoformat(),
            }
        )
    return output


def assign_study_ids(rows: list[dict], zeya_user_ids: Iterable[str]) -> list[dict]:
    """Replace ``user_key`` with Zeya's STUDY_#### ids over Zeya users plus OCS rows.

    Zeya numbers users by sorted user id. OCS-only keys start with "ocs:", which sorts
    after every UUID, so ids already used in Zeya exports stay the same.
    """
    keys = sorted(set(zeya_user_ids) | {r["user_key"] for r in rows})
    id_map = {key: f"STUDY_{i + 1:04d}" for i, key in enumerate(keys)}
    return [{"study_id": id_map[r["user_key"]], **{k: v for k, v in r.items() if k != "user_key"}} for r in rows]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ocs-export", required=True, help="CSV exported from the OCS chatbot sessions page")
    parser.add_argument("--zeya-users", help="CSV with user_id,whatsapp_id from the Zeya database")
    parser.add_argument("--out", help="output path (default: stdout)")
    args = parser.parse_args(argv)

    with open(args.ocs_export, newline="", encoding="utf-8") as f:
        ocs_rows = list(csv.DictReader(f))

    wa_id_to_user_id: dict[str, str] = {}
    if args.zeya_users:
        with open(args.zeya_users, newline="", encoding="utf-8") as f:
            wa_id_to_user_id = {_digits(r["whatsapp_id"]): r["user_id"] for r in csv.DictReader(f)}

    rows = assign_study_ids(convert_ocs_export(ocs_rows, wa_id_to_user_id), wa_id_to_user_id.values())

    out = open(args.out, "w", newline="", encoding="utf-8") if args.out else sys.stdout
    try:
        writer = csv.writer(out)
        writer.writerow(ZEYA_COLUMNS)
        for row in rows:
            writer.writerow([row[column] for column in ZEYA_COLUMNS])
    finally:
        if out is not sys.stdout:
            out.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
