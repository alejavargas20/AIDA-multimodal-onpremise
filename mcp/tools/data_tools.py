# mcp/tools/data_tools.py
try:
    from agents.data.data_logic import process
except Exception as e:

    def process(payload: dict) -> dict:
        return {"data": None, "status": "mock", "error": str(e)}


def data_process(payload: dict) -> dict:
    try:
        from agents.data.data_logic import process

        return process(payload)
    except Exception:
        return {"data": None, "status": "mock"}


TOOL_REGISTRY = {"data.process": data_process}
