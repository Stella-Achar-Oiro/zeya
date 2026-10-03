"""
Structural guarantees of the generated OCS pipeline.

These tests read the pipeline as a graph and check that the danger gate is the
only way in, that the emergency branch has no LLM node, and that every LLM node
can only be reached through the router's SAFE handle.
"""

import json

import pytest

from ocs.build_pipeline import COMMITTED_PIPELINE, SYSTEM_PROMPT_FILE, build_pipeline
from ocs.tests.conftest import NODES, module_constant

# Every OCS node type that calls an LLM (apps/pipelines/nodes/nodes.py).
LLM_NODE_TYPES = {
    "LLMResponse",
    "LLMResponseWithPrompt",
    "RouterNode",
    "AssistantNode",
    "ExtractStructuredData",
    "ExtractParticipantData",
}


@pytest.fixture(scope="module")
def pipeline():
    return build_pipeline(llm_provider_id=1, llm_provider_model_id=2)


@pytest.fixture(scope="module")
def graph(pipeline):
    nodes = {n["id"]: n for n in pipeline["data"]["nodes"]}
    edges = pipeline["data"]["edges"]
    return nodes, edges


def _by_name(nodes, name):
    matches = [n for n in nodes.values() if n["data"]["params"]["name"] == name]
    assert len(matches) == 1, name
    return matches[0]


def _is_llm(node) -> bool:
    return node["data"]["type"] in LLM_NODE_TYPES or "llm_provider_id" in node["data"]["params"]


def _reachable(start_id, edges, skip=lambda edge: False):
    seen, stack = set(), [start_id]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(e["target"] for e in edges if e["source"] == current and not skip(e))
    return seen


def _outgoing(node_id, edges):
    return [e for e in edges if e["source"] == node_id]


def test_starts_with_gate_then_router(graph):
    nodes, edges = graph
    start = next(n for n in nodes.values() if n["type"] == "startNode")
    gate = _by_name(nodes, "danger_gate")
    router = _by_name(nodes, "danger_router")

    assert [e["target"] for e in _outgoing(start["id"], edges)] == [gate["id"]]
    assert [e["target"] for e in _outgoing(gate["id"], edges)] == [router["id"]]
    assert [e["source"] for e in edges if e["target"] == gate["id"]] == [start["id"]]


def test_danger_router_config(graph):
    nodes, _ = graph
    params = _by_name(nodes, "danger_router")["data"]["params"]

    assert _by_name(nodes, "danger_router")["data"]["type"] == "StaticRouterNode"
    assert params["data_source"] == "temp_state"
    assert params["route_key"] == "danger_route"
    assert params["keywords"] == ["EMERGENCY", "SAFE"]
    # A missing or unexpected route value falls to EMERGENCY, never to the LLM.
    assert params["keywords"][params["default_keyword_index"]] == "EMERGENCY"


def test_emergency_branch_has_no_llm(graph):
    nodes, edges = graph
    router = _by_name(nodes, "danger_router")
    (emergency_edge,) = [e for e in _outgoing(router["id"], edges) if e["sourceHandle"] == "output_0"]

    branch = _reachable(emergency_edge["target"], edges)

    assert _by_name(nodes, "emergency_response")["id"] in branch
    assert not [nodes[i]["data"]["params"]["name"] for i in branch if _is_llm(nodes[i])]


def test_llm_reachable_only_through_safe(graph):
    nodes, edges = graph
    start = next(n for n in nodes.values() if n["type"] == "startNode")
    router = _by_name(nodes, "danger_router")
    llm_ids = {i for i, n in nodes.items() if _is_llm(n)}
    assert llm_ids, "expected at least one LLM node"

    def is_safe_edge(edge):
        return edge["source"] == router["id"] and edge["sourceHandle"] == "output_1"

    assert not llm_ids & _reachable(start["id"], edges, skip=is_safe_edge)


def test_every_node_is_downstream_of_router(graph):
    nodes, edges = graph
    start = next(n for n in nodes.values() if n["type"] == "startNode")
    gate = _by_name(nodes, "danger_gate")
    router = _by_name(nodes, "danger_router")

    assert set(nodes) == {start["id"], gate["id"]} | _reachable(router["id"], edges)


def test_registration_router_defaults_away_from_llm(graph):
    nodes, edges = graph
    router = _by_name(nodes, "registration_router")
    params = router["data"]["params"]
    llm = _by_name(nodes, "llm")

    assert params["data_source"] == "temp_state"
    assert params["route_key"] == "registration_route"
    assert params["keywords"] == ["REPLY", "REGISTERED"]
    assert params["keywords"][params["default_keyword_index"]] == "REPLY"
    (registered_edge,) = [e for e in _outgoing(router["id"], edges) if e["sourceHandle"] == "output_1"]
    assert registered_edge["target"] == llm["id"]


@pytest.mark.parametrize("name", ["danger_gate", "emergency_response", "registration"])
def test_code_nodes_match_repository_sources(graph, name):
    nodes, _ = graph
    node = _by_name(nodes, name)

    assert node["data"]["type"] == "CodeNode"
    assert node["data"]["params"]["code"] == (NODES / f"{name}.py").read_text()


def test_system_prompt_is_zeya_prompt():
    assert SYSTEM_PROMPT_FILE.read_text() == module_constant("app/services/ai_engine.py", "SYSTEM_PROMPT")


def test_system_prompt_has_no_template_braces():
    # OCS formats the prompt as a template: a stray "{" or "}" fails at run time, and a
    # "{name}" would be read as a variable.
    prompt = SYSTEM_PROMPT_FILE.read_text()
    assert "{" not in prompt and "}" not in prompt


def test_llm_node_config(graph):
    nodes, _ = graph
    params = _by_name(nodes, "llm")["data"]["params"]

    assert params["prompt"] == SYSTEM_PROMPT_FILE.read_text() + "\n\n{temp_state.llm_context}"
    assert params["llm_provider_id"] == 1
    assert params["llm_provider_model_id"] == 2
    assert params["llm_model_parameters"] == {"temperature": 1.0}
    # Zeya kept the last 6 turns (12 messages) of LLM conversation only.
    assert params["history_type"] == "node"
    assert params["history_mode"] == "max_history_length"
    assert params["max_history_length"] == 12


def test_committed_pipeline_is_up_to_date():
    committed = json.loads(COMMITTED_PIPELINE.read_text())
    assert committed == build_pipeline(llm_provider_id=0, llm_provider_model_id=0), (
        "Run: python -m ocs.build_pipeline --write"
    )
