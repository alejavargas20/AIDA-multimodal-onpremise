# aida-multimodal-onpremise/mcp/tools/image_tools.py

try:
    from agents.voice.voice_logic import process
except ImportError:

    def process(payload: dict) -> dict:
        return {"text": "Ejemplo numero 1", "status": "mock"}


def voice_process(payload: dict) -> dict:
    """
    Tool MCP para el Agente de Voz.
    Payload define si es STT o TTS.
    """
    return process(payload)


TOOL_REGISTRY = {"voice.process": voice_process}
