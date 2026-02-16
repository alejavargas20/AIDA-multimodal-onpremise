#aida-multimodal-onpremise/mcp/tools/prompt_tools.py
# Tool MCP para el Prompt Optimizer

import sys
import os
from typing import Dict, Any


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)


try:
    # Import real 
    from agents.prompt_optimizer.optimizer_logic import process_request
    print("[MCP] Prompt Optimizer cargado correctamente.")
except ImportError as e:
    print(f"[MCP] No se pudo cargar el Prompt Optimizer: {e}")
    # Fallback SOLO si falla la importación
    def process_request(payload: dict) -> dict:
        return {
            "status": "error",
            "errors": [f"ImportError: {e}"]
        }
    


# Tool MCP que llama al Prompt Optimizer
def prompt_optimize(payload: dict) -> dict:
    """
    Tool MCP que llama al Prompt Optimizer.
    El MCP NO sabe como funciona el optimizer.
    Solo pasa el payload y devuelve el resultado.
    """
    # Llama a la función real del agente
    try:
        resultado = process_request(payload)
        return resultado
    except Exception as e:
        return {
            "status": "error",
            "errors": [f"Error in prompt_optimize: {e}"]
        }


# Registro de la tool en el MCP
TOOL_REGISTRY = {"prompt.optimize": prompt_optimize}
