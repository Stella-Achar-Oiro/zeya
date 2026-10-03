"""
Check that the pipeline deployed on Open Chat Studio matches this repository.

OCS has no per-node lock, so anyone with pipeline edit rights could change the
danger gate in the web UI. This check is the control for that (docs/ocs-migration.md,
rule 3). Run it after every deploy and on a schedule; it exits 1 on any difference.

    # Save the live pipeline (logged-in browser, or a session cookie):
    curl -s -b "sessionid=$OCS_SESSION" \\
        https://openchatstudio.co.ke/a/evarest/pipelines/data/<pipeline id>/ > live.json
    python -m ocs.check_drift live.json --llm-provider-id 7 --llm-provider-model-id 31

Compared: node set, node types, edges (by node name and handle), all Python node
code, router settings, the LLM prompt, history and model parameters.
The LLM provider and model ids are specific to the instance, so the expected values are
passed in. A model switched in the UI is reported as drift.
Ignored: node positions, labels and ids.
"""

import argparse
import json
import sys

from ocs.build_pipeline import build_pipeline

INSTANCE_PARAMS = ("llm_provider_id", "llm_provider_model_id")


def _flow(document: dict) -> dict:
    """Accept the GET pipeline_data response, a FlowPipelineData body, or a bare flow."""
    if "pipeline" in document:
        document = document["pipeline"]
    return document.get("data", document)


def _describe(flow: dict) -> tuple[dict, set]:
    names = {node["id"]: node["data"]["params"].get("name", node["id"]) for node in flow["nodes"]}
    nodes = {
        names[node["id"]]: {
            "type": node["data"]["type"],
            "params": {k: v for k, v in node["data"]["params"].items() if k not in INSTANCE_PARAMS},
        }
        for node in flow["nodes"]
    }
    edges = {
        (names.get(e["source"], e["source"]), e.get("sourceHandle") or "output", names.get(e["target"], e["target"]))
        for e in flow["edges"]
    }
    return nodes, edges


def find_drift(
    live_document: dict, llm_provider_id: int | None = None, llm_provider_model_id: int | None = None
) -> list[str]:
    """Return human-readable differences between the live pipeline and the repository."""
    expected_nodes, expected_edges = _describe(build_pipeline(0, 0)["data"])
    live_nodes, live_edges = _describe(_flow(live_document))
    problems = []

    for name in sorted(expected_nodes.keys() - live_nodes.keys()):
        problems.append(f"missing node: {name}")
    for name in sorted(live_nodes.keys() - expected_nodes.keys()):
        problems.append(f"unexpected node: {name} ({live_nodes[name]['type']})")

    for name in sorted(expected_nodes.keys() & live_nodes.keys()):
        expected, live = expected_nodes[name], live_nodes[name]
        if expected["type"] != live["type"]:
            problems.append(f"{name}: type is {live['type']}, expected {expected['type']}")
        for key, value in expected["params"].items():
            if live["params"].get(key) != value:
                problems.append(f"{name}: '{key}' differs from the repository")

    for edge in sorted(expected_edges - live_edges):
        problems.append("missing edge: {} [{}] -> {}".format(*edge))
    for edge in sorted(live_edges - expected_edges):
        problems.append("unexpected edge: {} [{}] -> {}".format(*edge))

    expected_ids = {"llm_provider_id": llm_provider_id, "llm_provider_model_id": llm_provider_model_id}
    for node in _flow(live_document)["nodes"]:
        params = node["data"]["params"]
        for key in INSTANCE_PARAMS:
            if key in params and expected_ids[key] is not None and params[key] != expected_ids[key]:
                problems.append(
                    f"{params.get('name', node['id'])}: '{key}' is {params[key]}, expected {expected_ids[key]}"
                )

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("live", help="JSON from GET /a/<team>/pipelines/data/<id>/ ('-' for stdin)")
    parser.add_argument("--llm-provider-id", type=int, required=True, help="the Gemini provider id on the instance")
    parser.add_argument("--llm-provider-model-id", type=int, required=True, help="the deployed model id")
    args = parser.parse_args(argv)

    with sys.stdin if args.live == "-" else open(args.live, encoding="utf-8") as f:
        problems = find_drift(json.load(f), args.llm_provider_id, args.llm_provider_model_id)

    if problems:
        print("DRIFT: the live pipeline does not match the repository", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print("OK: live pipeline matches the repository")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
