import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
NODES = REPO_ROOT / "ocs" / "nodes"

# Lets backend modules import app.core.config without production secrets.
os.environ.setdefault("DEBUG", "true")

for path in (REPO_ROOT, BACKEND):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def node_source(name: str) -> str:
    return (NODES / f"{name}.py").read_text()


@pytest.fixture
def danger_gate_source() -> str:
    return node_source("danger_gate")


def module_constant(relative_path: str, name: str):
    """Read a literal module-level constant from a backend file without importing it.

    Used for modules such as ai_engine.py and conversation_handler.py whose imports
    need API clients and Redis.
    """
    import ast

    tree = ast.parse((BACKEND / relative_path).read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)
