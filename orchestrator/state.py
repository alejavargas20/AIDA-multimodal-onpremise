from typing import TypedDict, List, Literal, Dict, Any, Optional


class OrchestratorState(TypedDict, total=False):

    # =========================
    # ENTRADA (Interfaz Web)
    # =========================
    user_id: str
    session_id: str
    input_type: Literal["text", "audio", "image", "pdf"]
    content: str
    metadata: Dict

    # Perfil usuario / conducta
    user_profile: Literal["tecnico", "no_tecnico"]

    # =========================
    # FASE 1 – ROUTING DE CANAL
    # =========================
    normalized_text: str
    preprocessing_source: Literal["text", "stt", "ocr"]

    # =========================
    # PROMPT OPTIMIZER
    # =========================
    optimized_text: str
    intent_json: Dict[str, Any]  # salida estructurada del prompt optimizer

    # =========================
    # FASE 2 – PLANIFICACIÓN
    # =========================
    intent: str
    plan: List[Dict[str, Any]]

    # =========================
    # FASE 3 – EJECUCIÓN
    # =========================
    agent_results: List[Dict[str, Any]]
    assembled_text: str

    # =========================
    # SALIDA FINAL
    # =========================
    final_text: str

    # =========================
    # ERRORES / TRAZAS
    # =========================
    errors: List[str]
