from orchestrator.state import OrchestratorState
from typing import TypedDict, List, Literal, Dict, Any, Optional


def mock_agent(agent_name: str, prompt: str) -> list[Dict[str, Any]]:
    # Devuelve bloques estructurados
    if agent_name == "agente_nlp":
        return [
            {
                "type": "text",
                "role": "explanation",
                "content": f"Explicación simulada de: {prompt}",
            }
        ]
    if agent_name == "agente_datos":
        return [
            {
                "type": "table",
                "role": "result_table",
                "data": [["col1", "col2"], [1, 2]],
            },
            {
                "type": "text",
                "role": "summary",
                "content": "Resumen de datos simulado.",
            },
        ]
    if agent_name == "agente_matematico":
        return [
            {
                "type": "text",
                "role": "calculation",
                "content": "Cálculo de riesgo simulado.",
            }
        ]
    if agent_name == "agente_reportes":
        return [
            {
                "type": "text",
                "role": "report",
                "content": "Contenido simulado de reporte.",
            }
        ]
    # Por defecto
    return [
        {"type": "text", "role": "generic", "content": "Respuesta genérica de agente."}
    ]


def execute_plan(state: OrchestratorState) -> OrchestratorState:
    text = state.get("normalized_text", "")
    results: list[Dict[str, Any]] = []

    for step in state.get("plan", []):
        agent_name = step["agent"]
        try:
            blocks = mock_agent(agent_name, text)
            results.extend(blocks)
            step["status"] = "done"
        except Exception as e:
            step["status"] = "error"
            err_block = {"type": "error", "role": agent_name, "content": str(e)}
            results.append(err_block)
            state["errors"].append(f"Error ejecutando {agent_name}: {e}")

    state["agent_results"] = results
    return state


def assemble_results(state: OrchestratorState) -> OrchestratorState:
    blocks = state.get("agent_results", [])

    texts = [
        b["content"]
        for b in blocks
        if b.get("type") == "text" and b.get("role") != "error"
    ]
    errors = [b["content"] for b in blocks if b.get("type") == "error"]

    assembled = "\n\n".join(texts) if texts else "No se generó contenido."
    if errors:
        assembled += "\n\n[AVISOS]\n" + "\n".join(errors)

    state["assembled_text"] = assembled
    return state


def behaviour_adaptation(state: OrchestratorState) -> OrchestratorState:
    profile = state.get("user_profile", "no_tecnico")
    text = state.get("assembled_text", "")

    if profile == "tecnico":
        # Perfil técnico: dejamos más detalle
        adapted = f"[Modo técnico]\n{text}"
    else:
        # Perfil no técnico: simplificar un poco (mock)
        adapted = f"[Modo sencillo]\n{text}"

    state["final_text"] = adapted
    return state
