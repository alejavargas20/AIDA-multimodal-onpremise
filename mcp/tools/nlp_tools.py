# mcp/tools/nlp_tools.py
import sys
import os
from typing import Dict, Any



ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

    
# Intentamos importar la lógica real del agente NLP
try:
    from agents.nlp.nlp_logic import process
    print("[MCP] NLP Agent cargado correctamente.")
except ImportError as e:
    print(f"[MCP] No se pudo cargar el NLP Agent: {e}")
    def process(payload: dict) -> dict:
        return {
            "status": "error",
            "errors": [f"ImportError: {e}"]

        }

def nlp_process(payload: dict) -> dict:
    """
    Tool MCP que llama al agente NLP.
    """
    return process(payload)


TOOL_REGISTRY = {
    "nlp.process": nlp_process
}

