# agents/prompt_optimizer/llm_client.py
from __future__ import annotations
import sys
import os
from typing import Dict, List

# Setup path para importar local_engine
current = os.path.dirname(os.path.abspath(__file__))
parent = os.path.dirname(current) # agents/
if parent not in sys.path:
    sys.path.append(parent)

try:
    from local_engine import generate_response
except ImportError:
    # Fallback si falla el import path
    def generate_response(msgs): raise ImportError("No se encontró local_engine")

class LLMClientError(RuntimeError):
    pass

def call_llm_chat(messages: List[Dict[str, str]]) -> str:
    """
    Llama al modelo Hugging Face cargado en memoria localmente.
    """
    try:
        # Llamada directa a la GPU
        return generate_response(messages)
        
    except Exception as exc:
        raise LLMClientError(f"Local Engine failed: {exc}") from exc
