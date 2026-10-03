"""
Build the Zeya Open Chat Studio pipeline from the sources in this directory.

    python -m ocs.build_pipeline --write
        Regenerate ocs/pipeline/zeya_pipeline.json (provider ids set to 0) for review.

    python -m ocs.build_pipeline --llm-provider-id 7 --llm-provider-model-id 31 > out.json
        Build a deployable copy with the instance's Gemini provider and model ids.

The output is OCS FlowPipelineData (apps/pipelines/flow.py), the body accepted by
POST /a/<team>/pipelines/data/<pk>/. See docs/ocs-migration.md for the shape.
"""

import argparse
import json
import sys
from pathlib import Path

OCS_DIR = Path(__file__).resolve().parent
NODES_DIR = OCS_DIR / "nodes"
SYSTEM_PROMPT_FILE = OCS_DIR / "prompts" / "system_prompt.txt"
COMMITTED_PIPELINE = OCS_DIR / "pipeline" / "zeya_pipeline.json"

PIPELINE_NAME = "Zeya antenatal education"


def _node(node_id: str, node_type: str, params: dict, x: int, y: int, flow_type: str = "pipelineNode") -> dict:
    return {
        "id": node_id,
        "type": flow_type,
        "position": {"x": x, "y": y},
        "data": {"id": node_id, "type": node_type, "label": "", "params": params},
    }


def _edge(source: str, target: str, source_handle: str = "output") -> dict:
    return {
        "id": f"{source}:{source_handle}->{target}",
        "source": source,
        "target": target,
        "sourceHandle": source_handle,
        "targetHandle": "input",
    }


def _code(name: str) -> str:
    return (NODES_DIR / f"{name}.py").read_text()


def build_pipeline(llm_provider_id: int, llm_provider_model_id: int) -> dict:
    nodes = [
        _node("start", "StartNode", {"name": "start"}, 0, 200, flow_type="startNode"),
        _node("danger_gate", "CodeNode", {"name": "danger_gate", "code": _code("danger_gate")}, 300, 200),
        _node(
            "danger_router",
            "StaticRouterNode",
            {
                "name": "danger_router",
                "data_source": "temp_state",
                "route_key": "danger_route",
                # output_0 = EMERGENCY, output_1 = SAFE. EMERGENCY is the default route.
                "keywords": ["EMERGENCY", "SAFE"],
                "default_keyword_index": 0,
                "tag_output_message": True,
            },
            600,
            200,
        ),
        _node(
            "emergency_response",
            "CodeNode",
            {"name": "emergency_response", "code": _code("emergency_response")},
            900,
            0,
        ),
        _node("registration", "CodeNode", {"name": "registration", "code": _code("registration")}, 900, 350),
        _node(
            "registration_router",
            "StaticRouterNode",
            {
                "name": "registration_router",
                "data_source": "temp_state",
                "route_key": "registration_route",
                # output_0 = REPLY, output_1 = REGISTERED. REPLY is the default route.
                "keywords": ["REPLY", "REGISTERED"],
                "default_keyword_index": 0,
                "tag_output_message": False,
            },
            1200,
            350,
        ),
        _node(
            "llm",
            "LLMResponseWithPrompt",
            {
                "name": "llm",
                "llm_provider_id": llm_provider_id,
                "llm_provider_model_id": llm_provider_model_id,
                # Zeya called Gemini with no generation config, so it ran at the model's default
                # temperature (1.0 for Gemini 3). OCS would otherwise default to 0.7.
                "llm_model_parameters": {"temperature": 1.0},
                "prompt": SYSTEM_PROMPT_FILE.read_text() + "\n\n{temp_state.llm_context}",
                "history_type": "node",
                "history_mode": "max_history_length",
                "max_history_length": 12,
            },
            1500,
            450,
        ),
        _node("end", "EndNode", {"name": "end"}, 1800, 200, flow_type="endNode"),
    ]
    edges = [
        _edge("start", "danger_gate"),
        _edge("danger_gate", "danger_router"),
        _edge("danger_router", "emergency_response", "output_0"),
        _edge("danger_router", "registration", "output_1"),
        _edge("emergency_response", "end"),
        _edge("registration", "registration_router"),
        _edge("registration_router", "end", "output_0"),
        _edge("registration_router", "llm", "output_1"),
        _edge("llm", "end"),
    ]
    return {"name": PIPELINE_NAME, "data": {"nodes": nodes, "edges": edges}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help=f"write {COMMITTED_PIPELINE.relative_to(OCS_DIR.parent)}")
    parser.add_argument("--llm-provider-id", type=int, default=0)
    parser.add_argument("--llm-provider-model-id", type=int, default=0)
    args = parser.parse_args(argv)

    pipeline = build_pipeline(args.llm_provider_id, args.llm_provider_model_id)
    output = json.dumps(pipeline, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        COMMITTED_PIPELINE.write_text(output)
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
