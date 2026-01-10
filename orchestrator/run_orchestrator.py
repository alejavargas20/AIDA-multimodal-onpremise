from orchestrator.graph import orchestrator_app
from typing import TypedDict, List, Literal, Dict, Any, Optional


def run_orchestrator(
    user_id: str,
    session_id: str,
    input_type: Literal["text", "audio", "image", "pdf"],
    content: str,
    metadata: Dict,
    user_profile: Literal[
        "tecnico", "no_tecnico"
    ] = "no_tecnico",  # Mas bien un diccionario
):

    initial_state = {
        "user_id": user_id,
        "session_id": session_id,
        "input_type": input_type,
        "content": content,
        "metadata": metadata,
        "user_profile": user_profile,
    }

    return orchestrator_app.invoke(initial_state)


if __name__ == "__main__":
    # Demo sencilla
    result = run_orchestrator(
        user_id="123",
        session_id="abc",
        input_type="audio",
        content="Explicame que es la mora",
        metadata={},
        user_profile="no_tecnico",
    )

    print(result["assembled_text"])

# exec(open("orchestrator/run_orchestrator.py").read())
# py mcp/mcp_server.py
