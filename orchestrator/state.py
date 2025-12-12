from typing import TypedDict, List, Literal, Dict, Any, Optional


class OrchestratorState(TypedDict, total=False):

    # Entrada: Coge el input de la web
    user_id: str
    session_id: str
    input_type: Literal["text", "audio", "image", "pdf"]
    raw_input: str  # texto, audio, foto...
    # Perfil usuario / conducta
    user_profile: Literal["tecnico", "no_tecnico"]

    # FASE 1: ROUTING DE CANAL
    #  Elige que agente tiene que desencriptar el input del usuario
    normalized_text: str
    preprocessing_source: Literal["text", "stt", "ocr"]

    # Fase 2: ROUTING DE TAREA
    # Una vez que el agente ha normalizado el texto, se elabora un plan de ejecución
    intent: Optional[
        Literal[
            "EXPLICACION_TEO", "CONSULTA_DATOS", "ANALISIS_RIESGO", "REPORTE", "GENERAL"
        ]
    ]
    plan: List[Dict[str, Any]]  # p.ej. [{"agent": "agente_datos", "status": "pending"}]

    # Resultados de agentes
    agent_results: List[Dict[str, Any]]  # lista de bloques
    assembled_text: str
    final_text: str

    # Errores / trazas
    errors: List[str]
