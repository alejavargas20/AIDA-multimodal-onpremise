# mcp/tools/nlp_tools.py

try:
    from agents.nlp.nlp_logic import process
except ImportError:
    def process(payload: dict) -> dict:
        return {
            "output": "mock nlp output",
            "status": "mock"
        }

def nlp_process(payload: dict) -> dict:
    return process(payload)

TOOL_REGISTRY = {
    "nlp.process": nlp_process
}

