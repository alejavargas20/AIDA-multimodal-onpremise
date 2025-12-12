from langgraph.graph import StateGraph, END
from orchestrator.state import OrchestratorState
from orchestrator.nodes_phase_1 import phase1_router
from orchestrator.nodes_phase_2 import phase2_planner
from orchestrator.nodes_phase_3 import (
    assemble_results,
    behaviour_adaptation,
    execute_plan,
)

graph = StateGraph(OrchestratorState)


# Nodo de entrada
def input_node(state: OrchestratorState) -> OrchestratorState:
    state.setdefault("errors", [])
    state.setdefault("agent_results", [])
    state.setdefault("plan", [])
    return state


# Nodos
graph.add_node("input", input_node)
graph.add_node("phase1_router", phase1_router)
# Hay que añadir el nodo del propt_optimizer
graph.add_node("phase2_planner", phase2_planner)
graph.add_node("execute_plan", execute_plan)
graph.add_node("assemble_results", assemble_results)
graph.add_node("conducta", behaviour_adaptation)

# Edges
graph.set_entry_point("input")
graph.add_edge("input", "phase1_router")
graph.add_edge("phase1_router", "phase2_planner")
# Hay que añadir el edge del propt_optimizer
graph.add_edge("phase2_planner", "execute_plan")
graph.add_edge("execute_plan", "assemble_results")
graph.add_edge("assemble_results", "conducta")
graph.add_edge("conducta", END)

# Compilar
orchestrator_app = graph.compile()
