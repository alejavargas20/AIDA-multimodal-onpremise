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
        input_type="text",
        content="¿Cuántos créditos se desembolsaron en los últimos 30 días?",
        metadata={},
        user_profile="no_tecnico",
    )

    print(result["assembled_text"])

# C:\Users\enrique.aramos\AppData\Local\anaconda3\python.exe
# exec(open("mcp/mcp_server.py").read())
# exec(open("orchestrator/run_orchestrator.py", encoding="utf-8").read())
