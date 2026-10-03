"""
The export adapter turns an OCS chatbot transcript export into Zeya's
conversations_export.csv (AnalyticsService.export_conversations_csv).
"""

import csv
import io
import json

import pytest

from ocs.export_adapter import ZEYA_COLUMNS, assign_study_ids, convert_ocs_export, main

REGISTERED = {
    "consent_given": True,
    "registration_complete": True,
    "gestational_age_at_enrollment": 20,
    "enrolled_at": "2026-09-01T09:00:00+00:00",
    "study_group": "intervention",
    "language_preference": "en",
}


def _row(trace, message_type, content, date, data, tags="", participant="+254700000001", public_id="p-1"):
    return {
        "Message ID": f"{trace}-{message_type}",
        "Message Date": date,
        "Message Type": message_type,
        "Message Content": content,
        "Platform": "WhatsApp",
        "Session Tags": "",
        "Session Comments": "",
        "Session ID": "s-1",
        "Session State": "{}",
        "Chatbot ID": "c-1",
        "Chatbot Name": "Zeya",
        "Participant Name": "Akinyi",
        "Participant Identifier": participant,
        "Participant Public ID": public_id,
        "Message Tags": tags,
        "Message Comments": "",
        "Trace ID": str(trace),
        "Participant Data": json.dumps(data),
    }


def _turn(trace, question, answer, start, end, data, tags="", **kwargs):
    return [
        _row(trace, "human", question, start, data, **kwargs),
        _row(trace, "ai", answer, end, data, tags=tags, **kwargs),
    ]


def test_columns_match_zeya_export():
    assert ZEYA_COLUMNS == [
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


def test_normal_turn():
    rows = convert_ocs_export(
        _turn(
            1,
            "What should I eat?",
            "Eat greens, Mama.",
            "2026-09-15 10:00:00+00:00",
            "2026-09-15 10:00:02.500000+00:00",
            REGISTERED,
            tags="danger_router:SAFE",
        ),
        phone_to_user_id={},
    )

    incoming, outgoing = rows
    assert incoming == {
        "user_key": "ocs:p-1",
        "study_group": "intervention",
        "direction": "incoming",
        "message_text": "What should I eat?",
        "gestational_age": 22,  # 20 weeks + 14 days
        "danger_sign": False,
        "danger_keywords": "",
        "response_time_ms": "",
        "timestamp": "2026-09-15T10:00:00+00:00",
    }
    assert outgoing["direction"] == "outgoing"
    assert outgoing["danger_sign"] is False
    assert outgoing["response_time_ms"] == 2500
    assert outgoing["timestamp"] == "2026-09-15T10:00:02.500000+00:00"


def test_danger_turn_restores_keyword_order():
    tags = (
        "danger_keyword:bleeding:heavy bleeding, danger_keyword:headache_vision:severe headache, "
        "danger_router:EMERGENCY, danger_sign:bleeding, danger_sign:headache_vision"
    )
    rows = convert_ocs_export(
        _turn(
            2,
            "severe headache and heavy bleeding",
            "URGENT: ...",
            "2026-09-15 10:00:00+00:00",
            "2026-09-15 10:00:00.040000+00:00",
            REGISTERED,
            tags=tags,
        ),
        phone_to_user_id={},
    )

    incoming, outgoing = rows
    assert incoming["danger_sign"] is False  # Zeya flags the outgoing row only
    assert outgoing["danger_sign"] is True
    # Zeya order is category order: bleeding before headache_vision.
    assert outgoing["danger_keywords"] == "heavy bleeding, severe headache"


def test_drops_rows_zeya_never_logged():
    pending = REGISTERED | {"registration_complete": False}
    rows = convert_ocs_export(
        _turn(
            3,
            "Hi",
            "Welcome...",
            "2026-09-01 09:00:00+00:00",
            "2026-09-01 09:00:01+00:00",
            pending,
            tags="registration, registration:first_contact",
        )
        + _turn(
            4,
            "yes",
            "Thank you for consenting...",
            "2026-09-01 09:01:00+00:00",
            "2026-09-01 09:01:01+00:00",
            pending,
            tags="registration",
        )
        + _turn(5, "Hello", "Hi Mama", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:01+00:00", REGISTERED),
        phone_to_user_id={},
    )

    assert [(r["direction"], r["message_text"]) for r in rows] == [
        ("incoming", "yes"),  # Zeya logged registration answers but not its replies
        ("incoming", "Hello"),
        ("outgoing", "Hi Mama"),
    ]


def test_drops_participants_who_never_consented():
    declined = {"consent_given": False, "consent_declined": True, "study_group": "intervention"}
    rows = convert_ocs_export(
        _turn(
            6,
            "no",
            "Thank you for your response...",
            "2026-09-01 09:01:00+00:00",
            "2026-09-01 09:01:01+00:00",
            declined,
            tags="registration",
            participant="+254799",
            public_id="p-2",
        )
        + _turn(7, "Hello", "Hi", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:01+00:00", REGISTERED),
        phone_to_user_id={},
    )

    assert {r["user_key"] for r in rows} == {"ocs:p-1"}


def test_gestational_age_blank_before_registration():
    pending = {"consent_given": True, "enrolled_at": "2026-09-01T09:00:00+00:00", "study_group": "control"}
    rows = convert_ocs_export(
        _turn(
            8,
            "Akinyi",
            "Nice to meet you",
            "2026-09-01 09:02:00+00:00",
            "2026-09-01 09:02:01+00:00",
            pending,
            tags="registration",
        )
        + _turn(9, "Hello", "Hi", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:01+00:00", REGISTERED),
        phone_to_user_id={},
    )

    assert rows[0]["gestational_age"] == ""
    assert rows[0]["study_group"] == "control"


def test_links_existing_zeya_users_by_phone():
    rows = convert_ocs_export(
        _turn(
            10,
            "Hello",
            "Hi",
            "2026-09-15 10:00:00+00:00",
            "2026-09-15 10:00:01+00:00",
            REGISTERED,
            participant="+254 700 000 001",
        ),
        phone_to_user_id={"254700000001": "0f3c9a2e-0000-0000-0000-000000000001"},
    )

    assert {r["user_key"] for r in rows} == {"0f3c9a2e-0000-0000-0000-000000000001"}


def test_study_ids_keep_zeya_numbering():
    zeya_user_ids = ["b0000000-0000-0000-0000-000000000000", "a0000000-0000-0000-0000-000000000000"]
    rows = [
        {"user_key": "ocs:p-9"},
        {"user_key": "b0000000-0000-0000-0000-000000000000"},
        {"user_key": "ocs:p-1"},
    ]

    numbered = assign_study_ids(rows, zeya_user_ids)

    # Zeya numbers sorted user ids; OCS-only keys ("ocs:...") sort after every UUID,
    # so existing study ids do not change.
    assert [r["study_id"] for r in numbered] == ["STUDY_0004", "STUDY_0002", "STUDY_0003"]
    assert "user_key" not in numbered[0]


def test_cli_writes_zeya_csv(tmp_path):
    ocs_csv = tmp_path / "ocs.csv"
    with ocs_csv.open("w", newline="") as f:
        rows = _turn(11, "Hello", "Hi", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:01+00:00", REGISTERED)
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    zeya_users = tmp_path / "users.csv"
    zeya_users.write_text("user_id,phone_number\na0000000-0000-0000-0000-000000000000,254711111111\n")
    out = tmp_path / "out.csv"

    assert main(["--ocs-export", str(ocs_csv), "--zeya-users", str(zeya_users), "--out", str(out)]) == 0

    result = list(csv.reader(io.StringIO(out.read_text())))
    assert result[0] == ZEYA_COLUMNS
    assert result[1] == [
        "STUDY_0002",
        "intervention",
        "incoming",
        "Hello",
        "22",
        "False",
        "",
        "",
        "2026-09-15T10:00:00+00:00",
    ]
    assert result[2][2] == "outgoing" and result[2][7] == "1000"


@pytest.mark.parametrize("bad", ["not json", ""])
def test_tolerates_missing_participant_data(bad):
    row = _turn(12, "Hello", "Hi", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:01+00:00", REGISTERED)
    row[0]["Participant Data"] = bad

    rows = convert_ocs_export(row, phone_to_user_id={})

    assert rows[0]["gestational_age"] == ""


def _blank_trace(rows):
    # OCS only fills "Trace ID" when an external tracing provider (e.g. Langfuse) is set up.
    for row in rows:
        row["Trace ID"] = ""
    return rows


def _session(rows, session_id):
    for row in rows:
        row["Session ID"] = session_id
    return rows


def test_blank_trace_ids_pair_by_session_and_order():
    pending = REGISTERED | {"registration_complete": False}
    other = _session(
        _turn(
            20,
            "Hi",
            "Welcome...",
            "2026-09-01 09:00:00+00:00",
            "2026-09-01 09:00:01+00:00",
            pending,
            tags="registration, registration:first_contact",
            participant="+254799",
            public_id="p-2",
        ),
        "s-2",
    )
    mine = _session(
        _turn(21, "Hello", "Hi Mama", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:01.250000+00:00", REGISTERED),
        "s-1",
    )
    later = _session(
        _turn(
            22,
            "yes",
            "Thank you for consenting...",
            "2026-09-01 09:01:00+00:00",
            "2026-09-01 09:01:01+00:00",
            REGISTERED,
            tags="registration",
            participant="+254799",
            public_id="p-2",
        ),
        "s-2",
    )

    rows = convert_ocs_export(_blank_trace(other + mine + later), phone_to_user_id={})

    assert [(r["user_key"], r["direction"], r["message_text"]) for r in rows] == [
        ("ocs:p-2", "incoming", "yes"),
        ("ocs:p-1", "incoming", "Hello"),
        ("ocs:p-1", "outgoing", "Hi Mama"),
    ]
    assert rows[2]["response_time_ms"] == 1250


def test_reply_pairs_with_preceding_message_in_same_session():
    # Rows from two sessions interleaved in file order.
    a = _session(_turn(30, "A?", "A!", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:03+00:00", REGISTERED), "s-a")
    b = _session(
        _turn(
            31,
            "B?",
            "B!",
            "2026-09-15 10:00:01+00:00",
            "2026-09-15 10:00:02+00:00",
            REGISTERED,
            participant="+254711",
            public_id="p-b",
        ),
        "s-b",
    )

    rows = convert_ocs_export(_blank_trace([a[0], b[0], b[1], a[1]]), phone_to_user_id={})

    times = {r["message_text"]: r["response_time_ms"] for r in rows if r["direction"] == "outgoing"}
    assert times == {"A!": 3000, "B!": 1000}


def test_message_without_reply_is_kept():
    rows = _turn(40, "Hello", "unused", "2026-09-15 10:00:00+00:00", "2026-09-15 10:00:01+00:00", REGISTERED)

    result = convert_ocs_export(_blank_trace(rows[:1]), phone_to_user_id={})

    assert [(r["direction"], r["message_text"]) for r in result] == [("incoming", "Hello")]
