import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
NODES = REPO_ROOT / "ocs" / "nodes"

for path in (REPO_ROOT, BACKEND):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def node_source(name: str) -> str:
    return (NODES / f"{name}.py").read_text()


@pytest.fixture
def danger_gate_source() -> str:
    return node_source("danger_gate")
