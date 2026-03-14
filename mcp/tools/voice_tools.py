# aida-multimodal-onpremise/mcp/tools/voice_tools.py

import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

try:
    #from agents.voice.voice_logic import process
    print("[MCP] VOICE Agent cargado correctamente.")

except Exception as e:
    print(f"[MCP] No se pudo cargar VOICE Agent: {e}")
    
    def process(payload: dict) -> dict:
        return {
            "status": "error",
            "error": "El módulo de voz no está disponible.",
            "text": ""
        }

def voice_process(payload: dict) -> dict:
    return process(payload)

TOOL_REGISTRY = {
    "voice.process": voice_process
}