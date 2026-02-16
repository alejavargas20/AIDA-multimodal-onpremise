# aida-multimodal-onpremise/orchestrator/run_orchestrator.py

from orchestrator.graph import orchestrator_app
from typing import TypedDict, List, Literal, Dict, Any, Optional
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.db.history import get_recent_history 

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
    # RECUPERAR HISTORIAL REAL DESDE SQL SERVER
    print(f"[Orchestrator] Cargando historial para sesión {session_id}...")
    chat_history_text = get_recent_history(session_id, limit=5)
    # INYECTAR EN EL ESTADO INICIAL
    initial_state = {
        "user_id": user_id,
        "session_id": session_id,
        "input_type": input_type,
        "content": content,
        "metadata": metadata,
        "user_profile": user_profile,
        "chat_history": chat_history_text, 
    }

    return orchestrator_app.invoke(initial_state)
