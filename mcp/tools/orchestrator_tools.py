# mcp/tools/orchestrator_tools.py

import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from orchestrator.run_orchestrator import run_orchestrator


def orchestrator_entry(payload: dict) -> dict:
    result = run_orchestrator(
        user_id=payload["user_id"],
        session_id=payload["session_id"],
        input_type=payload["input_type"],
        content=payload["content"],
        metadata=payload.get("metadata", {}),
        user_profile=payload.get("user_profile", "no_tecnico")
    )

    return {
        "output_type": "text",
        "content": result.get("final_text") or result.get("assembled_text", "")
    }


TOOL_REGISTRY = {
    "orchestrator.entry": orchestrator_entry
}
    