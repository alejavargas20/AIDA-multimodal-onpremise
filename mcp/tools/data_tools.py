# mcp/tools/data_tools.py

try:
    from agents.data.data_logic import process
except ImportError:
    def process(payload: dict) -> dict:
        return {
            "data": None,
            "status": "mock"
        }

def data_process(payload: dict) -> dict:
    return process(payload)

TOOL_REGISTRY = {
    "data.process": data_process
}

