# aida-multimodal-onpremise/mcp/tools/image_tools.py

import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

try:
    #from agents.image.image_logic import process
    print("[MCP] Image Agent cargado correctamente.")
except Exception as e:
    print(f"[MCP] No se pudo cargar el Image Agent: {e}")
    def process(payload: dict) -> dict:
        return {
            "status": "error",
            "errors": [f"ImportError: {e}"]
        }

def image_process(payload: dict) -> dict:
    """
    Tool MCP para el Agente de Imagen.
    """
    return process(payload)

TOOL_REGISTRY = {
    "image.process": image_process
}
