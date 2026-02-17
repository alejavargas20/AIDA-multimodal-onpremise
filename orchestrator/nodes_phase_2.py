# aida-multimodal-onpremise/orchestrator/nodes_phase_2.py
from orchestrator.state import OrchestratorState
from orchestrator.mcp_client import call_mcp
import json

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
    context = state.get("file_context", "")      # El PDF/Imagen puede tener contexto adicional
    chat_history = state.get("chat_history", "")  # Historial recuperado en Fase 1

    if not text:
        state["errors"].append("Prompt optimizer: no hay normalized_text.")
        return state

    try:
        
        # Combinamos la memoria de la conversación con el contenido del archivo
        full_context = ""
        if chat_history:
            full_context += f"--- MEMORIA DE CONVERSACIÓN RECIENTE ---\n{chat_history}\n\n"
        if context:
            full_context += f"--- CONTENIDO DEL ARCHIVO ADJUNTO ---\n{context}\n"
        
        
        payload = {
            "user_text": text,
            "context": full_context,  # Pasamos el contexto al prompt optimizer
            "metadata": state.get("metadata", {}),
            "chat_history": state.get("chat_history", "") # Pasamos el historial al prompt optimizer
        }

        results = call_mcp("prompt.optimize", payload)
        state["optimized_text"] = results.get("optimized_prompt", "")
        state["intent_json"] = results.get("intent_plan")
        
        print("\n===== PROMPT OPTIMIZER FULL OUTPUT =====")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        print("=======================================\n")

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
    global_metadata = state.get("metadata", {})
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
                "action": "reason",
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
        task_metadata = t.get("metadata", {})
        combined_metadata = {**global_metadata, **task_metadata}
        plan.append(
            {
                "agent": normalize_agent_name(t.get("agent")),
                "action": t.get("action", "run"),
                "input": t.get("input", {}),
                "metadata": combined_metadata,
                "status": "pending",
            }
        )

    state["plan"] = plan
    print(state["plan"])

    return state
