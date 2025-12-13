from typing import Literal
from graph import orchestrator_app
from state import OrchestratorState

def run_orchestrator(
    user_id: str,
    session_id: str,
    input_type: Literal["text", "audio", "image", "pdf"],
    raw_input: str,
    user_profile: Literal["tecnico", "no_tecnico"] = "no_tecnico",
) -> OrchestratorState:
    initial_state: OrchestratorState = {
        "user_id": user_id,
        "session_id": session_id,
        "input_type": input_type,
        "raw_input": raw_input,
        "user_profile": user_profile,
    }

    return orchestrator_app.invoke(initial_state)

if __name__ == "__main__":
    # Demo sencilla
    result = run_orchestrator(
        user_id="123",
        session_id="abc",
        input_type="pdf",
        raw_input="Explícame qué es la mora",
        user_profile="no_tecnico",
    )
    print(result["final_text"])