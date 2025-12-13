from state import OrchestratorState


def mock_intent_classifier(text: str) -> str:
    t = text.lower()
    if "saldo" in t or "tabla" in t:
        return "CONSULTA_DATOS"
    if "riesgo" in t or "probabilidad" in t:
        return "ANALISIS_RIESGO"
    if "reporte" in t or "informe" in t:
        return "REPORTE"
    if "explica" in t or "qué es" in t:
        return "EXPLICACION_TEO"
    return "GENERAL"


def phase2_planner(state: OrchestratorState) -> OrchestratorState:
    text = state.get("normalized_text", "")
    if not text:
        state["errors"].append("No hay texto normalizado en Fase 2.")
        return state

    intent = mock_intent_classifier(text)
    state["intent"] = intent

    plan = []
    if intent == "EXPLICACION_TEO":
        plan.append({"agent": "agente_nlp", "status": "pending"})
    elif intent == "CONSULTA_DATOS":
        plan.append({"agent": "agente_datos", "status": "pending"})
    elif intent == "ANALISIS_RIESGO":
        plan.append({"agent": "agente_matematico", "status": "pending"})
    elif intent == "REPORTE":
        # ejemplo: primero datos, luego reporte
        plan.append({"agent": "agente_datos", "status": "pending"})
        plan.append({"agent": "agente_reportes", "status": "pending"})
    else:  # GENERAL
        plan.append({"agent": "agente_nlp", "status": "pending"})

    state["plan"] = plan
    return state
