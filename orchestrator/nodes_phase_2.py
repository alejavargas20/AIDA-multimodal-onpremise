from orchestrator.state import OrchestratorState
from orchestrator.mcp_client import call_mcp


def normalize_agent_name(agent: str) -> str:
    if not agent:
        return "nlp.process"

    if agent.endswith(".process"):
        return agent

    return f"{agent}.process"


def prompt_optimizer(state: OrchestratorState) -> OrchestratorState:
    print("\nPROMPT OPTIMIZER")
    state.setdefault("errors", [])
    text = state.get("normalized_text", "")

    if not text:
        state["errors"].append("Prompt optimizer: no hay normalized_text.")
        return state

    try:
        results = call_mcp("prompt.optimize", {"user_text": text})
        state["optimized_text"] = results.get("optimized_prompt", "")
        state["intent_json"] = results.get("intent_json")
        print(results)

        if not state["optimized_text"]:
            state["errors"].append("Prompt optimizer devolvió optimized_prompt vacío.")
            print(state["errors"])

    except Exception as e:
        state["errors"].append(f"Error en el Prompt Optimizer: {e}")
        print(state["errors"])

    return state


def phase2_planner(state: OrchestratorState) -> OrchestratorState:
    print("\nPHASE2")
    state.setdefault("errors", [])
    state.setdefault("plan", [])

    intent_json = state.get("intent_json") or {"intent": "unknown", "tasks": []}
    tasks = intent_json.get("tasks", [])
    intent = intent_json.get("intent", "unknown")

    # Guardamos la intención
    state["intent"] = intent

    # Si el prompt optimizer no dio tareas, fallback mínimo
    if not isinstance(tasks, list) or len(tasks) == 0:
        state["errors"].append(
            "Phase2: intent_json.tasks vacío. Usando fallback agente_nlp."
        )
        state["plan"] = [
            {
                "agent": "nlp.process",
                "action": "respond",
                "input": {
                    "text": state.get("optimized_text")
                    or state.get("normalized_text")
                    or ""
                },
                "status": "pending",
            }
        ]
        return state

    # Convertir tasks → plan (1:1)
    plan = []
    for t in tasks:
        plan.append(
            {
                "agent": normalize_agent_name(t.get("agent")),
                "action": t.get("action", "run"),
                "input": t.get("input", {}),
                "status": "pending",
            }
        )

    state["plan"] = plan
    print(state["plan"])

    return state
