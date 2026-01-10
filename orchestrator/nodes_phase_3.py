from orchestrator.state import OrchestratorState
from typing import TypedDict, List, Literal, Dict, Any, Optional
from orchestrator.mcp_client import call_mcp


def execute_plan(state: OrchestratorState) -> OrchestratorState:
    print("\nEXECUTE PLAN")
    state.setdefault("errors", [])
    plan = state.get("plan", [])
    results = []

    if not plan:
        state["errors"].append("ExecutePlan: plan vacío.")
        state["agent_results"] = []
        return state

    # Usamos el mejor texto para pasar como contexto
    base_text = state.get("optimized_text") or state.get("normalized_text") or ""

    for step in plan:
        tool_name = step.get("agent")  # <-- lo que viene del prompt optimizer
        action = step.get("action", "run")
        inp = step.get("input", {}) if isinstance(step.get("input", {}), dict) else {}

        if not tool_name:
            step["status"] = "error"
            state["errors"].append("ExecutePlan: step sin 'agent' (tool_name).")
            continue

        # Construimos payload para MCP (incluye action + contexto)
        payload = {
            **inp,
            "action": action,
            "context": {
                "user_id": state.get("user_id"),
                "session_id": state.get("session_id"),
                "text": base_text,
                "intent": state.get("intent"),
            },
        }

        try:
            print(tool_name)
            tool_result = call_mcp(tool_name, payload)
            results.append(
                {
                    "type": "tool_result",
                    "role": tool_name,
                    "action": action,
                    "content": tool_result,
                }
            )
            step["status"] = "done"

        except Exception as e:
            step["status"] = "error"
            err = f"ExecutePlan: error llamando a {tool_name}: {e}"
            state["errors"].append(err)
            results.append(
                {
                    "type": "error",
                    "role": tool_name,
                    "action": action,
                    "content": str(e),
                }
            )

    state["agent_results"] = results
    print(state["agent_results"])
    return state


def assemble_results(state: OrchestratorState) -> OrchestratorState:
    print("\nASSEMBLE RESULTS")
    blocks = state.get("agent_results", [])
    state.setdefault("errors", [])

    assembled_parts = []

    if not blocks:
        state["assembled_text"] = "No se generaron resultados por parte de los agentes."
        return state

    for block in blocks:
        block_type = block.get("type")
        role = block.get("role")
        action = block.get("action")
        content = block.get("content", {})

        # --- DATA AGENT ---
        if block_type == "tool_result" and role == "data.process":
            status = content.get("status", "unknown")
            data = content.get("data")

            if status != "mock" or data is not None:
                assembled_parts.append(
                    f"[DATOS]\nResultado de la consulta ({action}):\n{data}"
                )
            else:
                assembled_parts.append(
                    f"[DATOS]\nConsulta ejecutada ({action}), sin datos (mock)."
                )

        # --- NLP AGENT ---
        elif block_type == "tool_result" and role == "nlp.process":
            output = content.get("output")

            if output:
                assembled_parts.append(f"[ANÁLISIS]\n{output}")
            else:
                assembled_parts.append(
                    "[ANÁLISIS]\nEl agente NLP no devolvió contenido."
                )

        # --- ERROR ---
        elif block_type == "error":
            assembled_parts.append(f"[ERROR]\n{content}")

        # --- UNKNOWN BLOCK ---
        else:
            assembled_parts.append(f"[INFO]\nResultado no reconocido: {block}")

    # Unir todo en un solo texto
    state["assembled_text"] = "\n\n".join(assembled_parts)
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
