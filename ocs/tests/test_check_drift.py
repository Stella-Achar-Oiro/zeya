import copy
import json

import pytest

from ocs.build_pipeline import build_pipeline
from ocs.check_drift import find_drift, main


def _live(llm_provider_id=7, llm_provider_model_id=31):
    """Shape of GET /a/<team>/pipelines/data/<id>/."""
    pipeline = build_pipeline(llm_provider_id, llm_provider_model_id)
    return {"pipeline": {"id": 12, "name": pipeline["name"], "data": pipeline["data"], "errors": {}}}


def _node(document, name):
    return next(n for n in document["pipeline"]["data"]["nodes"] if n["data"]["params"]["name"] == name)


def test_deployed_copy_matches():
    assert find_drift(_live()) == []
    assert find_drift(_live(), llm_provider_id=7, llm_provider_model_id=31) == []


def test_detects_model_switched_in_ui():
    live = _live(llm_provider_id=7, llm_provider_model_id=44)

    assert find_drift(live, llm_provider_id=7, llm_provider_model_id=31) == [
        "llm: 'llm_provider_model_id' is 44, expected 31"
    ]


def test_detects_provider_switched_in_ui():
    live = _live(llm_provider_id=3, llm_provider_model_id=31)

    assert find_drift(live, llm_provider_id=7, llm_provider_model_id=31) == ["llm: 'llm_provider_id' is 3, expected 7"]


def test_ignores_positions_labels_and_provider_ids():
    live = _live(llm_provider_id=99, llm_provider_model_id=100)
    for node in live["pipeline"]["data"]["nodes"]:
        node["position"] = {"x": 1, "y": 2}
        node["data"]["label"] = "renamed in UI"

    assert find_drift(live) == []


def test_ignores_defaults_added_by_ocs():
    live = _live()
    _node(live, "danger_gate")["data"]["params"]["tag_output_message"] = False

    assert find_drift(live) == []


def test_detects_edited_gate_code():
    live = _live()
    gate = _node(live, "danger_gate")["data"]["params"]
    gate["code"] = gate["code"].replace(r"\bchills\b", r"\bchill\b")

    assert find_drift(live) == ["danger_gate: 'code' differs from the repository"]


def test_detects_changed_router_default():
    live = _live()
    _node(live, "danger_router")["data"]["params"]["default_keyword_index"] = 1

    assert find_drift(live) == ["danger_router: 'default_keyword_index' differs from the repository"]


def test_detects_llm_added_to_emergency_branch():
    live = _live()
    flow = live["pipeline"]["data"]
    extra = copy.deepcopy(_node(live, "llm"))
    extra["id"] = extra["data"]["id"] = "extra_llm"
    extra["data"]["params"]["name"] = "emergency_followup"
    flow["nodes"].append(extra)
    flow["edges"] = [e for e in flow["edges"] if e["source"] != "emergency_response"]
    flow["edges"] += [
        {"id": "a", "source": "emergency_response", "target": "extra_llm", "sourceHandle": "output"},
        {"id": "b", "source": "extra_llm", "target": "end", "sourceHandle": "output"},
    ]

    problems = find_drift(live)

    assert "unexpected node: emergency_followup (LLMResponseWithPrompt)" in problems
    assert "missing edge: emergency_response [output] -> end" in problems
    assert "unexpected edge: emergency_response [output] -> emergency_followup" in problems


def test_detects_edited_prompt_and_temperature():
    live = _live()
    params = _node(live, "llm")["data"]["params"]
    params["prompt"] += "\nAlso recommend herbal remedies."
    params["llm_model_parameters"] = {"temperature": 0.2}

    assert sorted(find_drift(live)) == [
        "llm: 'llm_model_parameters' differs from the repository",
        "llm: 'prompt' differs from the repository",
    ]


@pytest.mark.parametrize(("mutate", "code"), [(False, 0), (True, 1)])
def test_cli_exit_code(tmp_path, capsys, mutate, code):
    live = _live()
    if mutate:
        _node(live, "emergency_response")["data"]["params"]["code"] += "\n# edited"
    path = tmp_path / "live.json"
    path.write_text(json.dumps(live))

    assert main([str(path), "--llm-provider-id", "7", "--llm-provider-model-id", "31"]) == code


def test_cli_requires_expected_model(tmp_path):
    path = tmp_path / "live.json"
    path.write_text(json.dumps(_live()))

    with pytest.raises(SystemExit):
        main([str(path)])
