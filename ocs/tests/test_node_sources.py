"""Every node source must be accepted by the OCS Python-node validator."""

import ast

import pytest

from ocs.tests.conftest import NODES
from ocs.tests.sandbox import make_executor

NODE_FILES = sorted(p for p in NODES.glob("*.py") if p.name != "__init__.py")


def test_expected_nodes_exist():
    assert {p.stem for p in NODE_FILES} >= {"danger_gate", "emergency_response"}


@pytest.mark.parametrize("path", NODE_FILES, ids=lambda p: p.stem)
def test_source_passes_ocs_validation(path):
    make_executor(path.read_text())


@pytest.mark.parametrize("path", NODE_FILES, ids=lambda p: p.stem)
def test_source_has_only_main_at_top_level(path):
    # OCS exec()s node code with separate locals, so module-level names are invisible
    # inside main. Everything must live inside main.
    body = ast.parse(path.read_text()).body
    statements = [n for n in body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
    assert len(statements) == 1
    assert isinstance(statements[0], ast.FunctionDef) and statements[0].name == "main"


def test_sandbox_rejects_tuple_unpacking_assignment():
    # OCS provides _iter_unpack_sequence_ (for loops) but not _unpack_sequence_, so
    # "a, b = ..." fails at run time inside a node. This pins that constraint.
    from ocs.tests.sandbox import NodeHarness

    harness = NodeHarness("def main(input, **kwargs):\n    a, b = 1, 2\n    return a\n")
    with pytest.raises(NameError, match="_unpack_sequence_"):
        harness.run("x")
