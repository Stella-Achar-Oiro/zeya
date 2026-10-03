"""Behaviour of the danger-gate node inside the OCS Python-node sandbox."""

import pytest

from ocs.tests.danger_corpus import BILINGUAL_EXAMPLES, NEGATIVE_MESSAGES
from ocs.tests.sandbox import NodeHarness

BILINGUAL_CASES = [
    (category, language, message)
    for category, languages in BILINGUAL_EXAMPLES.items()
    for language, message in languages.items()
]


def test_all_eight_categories_covered_in_both_languages():
    assert len(BILINGUAL_EXAMPLES) == 8
    assert all(set(langs) == {"en", "sw"} for langs in BILINGUAL_EXAMPLES.values())


@pytest.mark.parametrize(("category", "language", "message"), BILINGUAL_CASES)
def test_category_routes_to_emergency(danger_gate_source, category, language, message):
    harness = NodeHarness(danger_gate_source)

    output = harness.run(message)

    assert harness.temp_state["danger_route"] == "EMERGENCY"
    assert category in harness.temp_state["danger_categories"]
    assert f"danger_sign:{category}" in harness.message_tags
    assert output == message


@pytest.mark.parametrize("message", NEGATIVE_MESSAGES)
def test_safe_message_routes_to_safe(danger_gate_source, message):
    harness = NodeHarness(danger_gate_source)

    output = harness.run(message)

    assert harness.temp_state["danger_route"] == "SAFE"
    assert harness.temp_state["danger_categories"] == []
    assert harness.temp_state["danger_keywords"] == []
    assert harness.message_tags == []
    assert output == message


def test_keywords_are_tagged_for_export(danger_gate_source):
    harness = NodeHarness(danger_gate_source)

    harness.run("I have severe headache and heavy\n bleeding")

    assert "danger_keyword:severe headache" in harness.message_tags
    assert "danger_keyword:heavy bleeding" in harness.message_tags


def test_keyword_tags_fit_ocs_tag_length(danger_gate_source):
    harness = NodeHarness(danger_gate_source)

    harness.run("heavy" + " " * 200 + "bleeding " + "water" + "\t" * 200 + "broke")

    assert all(len(tag) <= 100 for tag in harness.message_tags)
