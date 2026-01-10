from orchestrator.state import OrchestratorState
from orchestrator.mcp_client import call_mcp


def phase1_router(state: OrchestratorState) -> OrchestratorState:
    input_type = state["input_type"]
    raw = state["content"]
    print("PHASE1")
    state.setdefault("errors", [])

    try:
        if input_type == "text":
            state["normalized_text"] = raw
            state["preprocessing_source"] = "text"

        elif input_type == "audio":
            results = call_mcp(
                "voice.process", {"file_path": state["content"]}
            )  # Que más necesita el MCP en el payload
            state["normalized_text"] = results.get("text")
            state["preprocessing_source"] = "stt"

        elif input_type in ("image", "pdf"):
            results = call_mcp(
                "image.process", {"file_path": state["content"]}
            )  # Que más necesita el MCP en el payload
            state["normalized_text"] = results.get("text")
            state["preprocessing_source"] = "ocr"
        else:
            state["errors"].append(f"Tipo de input no soportado: {input_type}")

        print(state["normalized_text"])
        print(state["preprocessing_source"])
        if not state.get("normalized_text"):
            state["errors"].append("Fase 1: normalized_text vacío.")

    except Exception as e:
        state["errors"].append(f"Error en Fase 1: {e}")

    return state
