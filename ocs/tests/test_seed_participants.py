"""
seed_participants turns Zeya users into an OCS participant import CSV
(apps/participants/import_export.py: identifier, channel, name, data.* as JSON).
Imported participants must go straight to the LLM without registering again.
"""

import csv
import datetime
import io
import json

from ocs.seed_participants import OCS_COLUMNS, main, zeya_user_to_participant
from ocs.tests.conftest import node_source
from ocs.tests.sandbox import NodeHarness

# One row of the \copy in seed_participants.py, as psql writes it.
REGISTERED_USER = {
    "id": "0f3c9a2e-0000-0000-0000-000000000001",
    "whatsapp_id": "254700000001",
    "name": "Akinyi",
    "consent_given": "t",
    "consent_given_at": "2026-08-01 09:01:00.5+00",
    "gestational_age_at_enrollment": "18",
    "expected_delivery_date": "2027-01-02",
    "enrolled_at": "2026-08-01 09:00:00+00",
    "registration_complete": "t",
    "language_preference": "sw",
    "study_group": "control",
    "is_active": "t",
}


def _ocs_import_parse(row: dict) -> dict:
    """What OCS's process_participant_import stores as participant data."""
    data = {}
    for key, value in row.items():
        if key.startswith("data.") and value:
            try:
                data[key[5:]] = json.loads(value)
            except json.JSONDecodeError:
                data[key[5:]] = value
    if row.get("name"):
        data["name"] = row["name"]
    return data


def test_registered_user():
    row = zeya_user_to_participant(REGISTERED_USER)

    assert row["identifier"] == "254700000001"
    assert row["channel"] == "whatsapp"
    assert _ocs_import_parse(row) == {
        "welcome_sent": True,
        "consent_given": True,
        "consent_given_at": "2026-08-01T09:01:00.500000+00:00",
        "name": "Akinyi",
        "name_collected": True,
        "gestational_age_at_enrollment": 18,
        "expected_delivery_date": "2027-01-02",
        "enrolled_at": "2026-08-01T09:00:00+00:00",
        "registration_complete": True,
        "language_preference": "sw",
        "study_group": "control",
        "zeya_user_id": "0f3c9a2e-0000-0000-0000-000000000001",
    }


def test_imported_participant_skips_registration():
    data = _ocs_import_parse(zeya_user_to_participant(REGISTERED_USER))
    now = datetime.datetime(2026, 10, 3, 9, 0, tzinfo=datetime.UTC)
    harness = NodeHarness(node_source("registration"), participant_data=data, now=now)

    output = harness.run("Nifanye nini kuhusu kichefuchefu?")

    assert output == "Nifanye nini kuhusu kichefuchefu?"
    assert harness.temp_state["registration_route"] == "REGISTERED"
    # 18 weeks at enrolment + 63 days -> 27 weeks, third trimester; Swahili.
    assert harness.temp_state["llm_context"].startswith("User's current gestational age: 27 weeks.")
    assert harness.temp_state["llm_context"].endswith("User prefers Swahili. Respond in Swahili.")


def test_user_mid_registration_resumes_at_next_step():
    user = REGISTERED_USER | {
        "gestational_age_at_enrollment": "",
        "expected_delivery_date": "",
        "registration_complete": "f",
    }
    data = _ocs_import_parse(zeya_user_to_participant(user))

    output = NodeHarness(node_source("registration"), participant_data=data).run("hello")

    assert output == "Please enter a valid number of weeks (between 1 and 42). For example: 20"


def test_declined_user_is_marked_declined():
    user = REGISTERED_USER | {
        "consent_given": "f",
        "consent_given_at": "",
        "name": "",
        "is_active": "f",
        "registration_complete": "f",
        "gestational_age_at_enrollment": "",
    }

    data = _ocs_import_parse(zeya_user_to_participant(user))

    assert data["consent_given"] is False
    assert data["consent_declined"] is True
    assert "name_collected" not in data


def test_cli_skips_deactivated_consented_users(tmp_path, capsys):
    source = tmp_path / "users.csv"
    with source.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(REGISTERED_USER))
        writer.writeheader()
        writer.writerow(REGISTERED_USER)
        writer.writerow(REGISTERED_USER | {"whatsapp_id": "254700000002", "is_active": "f"})
    out = tmp_path / "participants.csv"

    assert main(["--zeya-users", str(source), "--out", str(out)]) == 0

    rows = list(csv.DictReader(io.StringIO(out.read_text())))
    assert [r["identifier"] for r in rows] == ["254700000001"]
    assert list(rows[0]) == OCS_COLUMNS
    assert "254700000002" in capsys.readouterr().err
