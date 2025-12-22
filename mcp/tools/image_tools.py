# aida-multimodal-onpremise/mcp/tools/image_tools.py

try:
    from agents.image.image_logic import process
except ImportError:
    def process(payload: dict) -> dict:
        return {
            "text": None,
            "status": "mock"
        }

def image_process(payload: dict) -> dict:
    """
    Tool MCP para el Agente de Imagen.
    """
    return process(payload)

TOOL_REGISTRY = {
    "image.process": image_process
}
