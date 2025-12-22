# aida-multimodal-onpremise/mcp/tools/behavior_tools.py

try:
    from agents.behavior_model.behavior_logic import process
except ImportError:
    def process(payload: dict) -> dict:
        return {
            "adaptation": {},
            "status": "mock"
        }


def behavior_process(payload: dict) -> dict:
    """
    Tool MCP para el modelo conductual (COM-B).
    El MCP no conoce el modelo interno.
    """
    return process(payload)


TOOL_REGISTRY = {
    "behavior.process": behavior_process
}
