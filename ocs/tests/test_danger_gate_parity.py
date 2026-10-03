"""
Parity between the OCS danger-gate node and backend/app/services/danger_signs.py.

The node source must contain exactly the same patterns (string and flags), in the
same order and categories, and must produce identical categories and keywords for
every message.
"""

import ast
import re

import pytest

from app.services.danger_signs import DANGER_SIGN_PATTERNS, detect_danger_signs
from ocs.tests.danger_corpus import (
    BILINGUAL_EXAMPLES,
    EDGE_CASE_MESSAGES,
    EXISTING_TEST_MESSAGES,
    NEGATIVE_MESSAGES,
    PATTERN_EXAMPLES,
)
from ocs.tests.sandbox import NodeHarness


def _node_patterns(source: str) -> list[tuple[str, str, int]]:
    """Extract (category, pattern, flags) from the node source without executing it."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Tuple) and len(node.elts) == 2):
            continue
        category, patterns = node.elts
        if not (isinstance(category, ast.Constant) and isinstance(patterns, ast.List)):
            continue
        for call in patterns.elts:
            assert isinstance(call, ast.Call), ast.dump(call)
            assert ast.unparse(call.func) == "re.compile", ast.unparse(call)
            pattern_arg, flag_arg = call.args
            flags = 0
            for flag_name in ast.unparse(flag_arg).split("|"):
                flags |= getattr(re, flag_name.strip().removeprefix("re."))
            found.append((category.value, pattern_arg.value, re.compile(pattern_arg.value, flags).flags))
    return found


def _original_patterns() -> list[tuple[str, str, int]]:
    return [
        (category, pattern.pattern, pattern.flags)
        for category, patterns in DANGER_SIGN_PATTERNS.items()
        for pattern in patterns
    ]


def _run_gate(source: str, message: str) -> NodeHarness:
    harness = NodeHarness(source)
    harness.run(message)
    return harness


def test_node_patterns_are_verbatim_copies(danger_gate_source):
    assert _node_patterns(danger_gate_source) == _original_patterns()


def test_original_has_expected_shape():
    # Guard against the original changing without the node being updated.
    assert list(DANGER_SIGN_PATTERNS) == [
        "bleeding",
        "headache_vision",
        "fever",
        "fetal_movement",
        "abdominal_pain",
        "water_breaking",
        "convulsions",
        "swelling",
    ]
    assert sum(len(p) for p in DANGER_SIGN_PATTERNS.values()) == 39


def test_every_pattern_has_an_example():
    covered = {(category, index) for category, index, _ in PATTERN_EXAMPLES}
    expected = {
        (category, index) for category, patterns in DANGER_SIGN_PATTERNS.items() for index in range(len(patterns))
    }
    assert covered == expected


@pytest.mark.parametrize(("category", "index", "message"), PATTERN_EXAMPLES)
def test_each_pattern_fires_in_node(danger_gate_source, category, index, message):
    target = DANGER_SIGN_PATTERNS[category][index]
    earlier = DANGER_SIGN_PATTERNS[category][:index]
    assert target.search(message), "example does not exercise its pattern"
    assert not any(p.search(message) for p in earlier), "an earlier pattern would match first"

    harness = _run_gate(danger_gate_source, message)

    assert category in harness.temp_state["danger_categories"]
    assert target.search(message).group() in harness.temp_state["danger_keywords"]


ALL_MESSAGES = (
    [m for _, _, m in PATTERN_EXAMPLES]
    + [m for langs in BILINGUAL_EXAMPLES.values() for m in langs.values()]
    + EXISTING_TEST_MESSAGES
    + NEGATIVE_MESSAGES
    + EDGE_CASE_MESSAGES
)


@pytest.mark.parametrize("message", ALL_MESSAGES)
def test_node_matches_original_exactly(danger_gate_source, message):
    expected = detect_danger_signs(message)
    harness = _run_gate(danger_gate_source, message)

    assert harness.temp_state["danger_categories"] == expected.categories
    assert harness.temp_state["danger_keywords"] == expected.keywords
    assert harness.temp_state["danger_route"] == ("EMERGENCY" if expected.detected else "SAFE")
