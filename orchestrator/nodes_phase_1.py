from orchestrator.state import OrchestratorState


def phase1_router(state: OrchestratorState) -> OrchestratorState:
    input_type = state["input_type"]
    raw = state["raw_input"]

    try:
        if input_type == "text":
            state["normalized_text"] = raw
            state["preprocessing_source"] = "text"

        elif input_type == "audio":
            # MOCK de STT: aquí luego llamas al agente Whisper real
            text = mock_stt(raw)
            state["normalized_text"] = text
            state["preprocessing_source"] = "stt"

        elif input_type in ("image", "pdf"):
            # MOCK de OCR
            text = mock_ocr(raw)
            state["normalized_text"] = text
            state["preprocessing_source"] = "ocr"
        else:
            state["errors"].append(f"Tipo de input no soportado: {input_type}")
    except Exception as e:
        state["errors"].append(f"Error en Fase 1: {e}")

    return state


def mock_stt(audio_path: str) -> str:
    # Aquí en el futuro: llamada a Agente Voz
    return "transcripción simulada de audio"


def mock_ocr(file_path: str) -> str:
    # Aquí en el futuro: llamada a Agente Imagen/OCR
    return "texto extraído simulado de imagen/pdf"
