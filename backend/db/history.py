# aida-multimodal-onpremise/backend/db/history.py
from backend.db.connection import get_db

def get_recent_history(session_id: str, limit: int = 5) -> str:
    """
    Recupera el historial reciente como TEXTO PLANO
    para inyectarlo en el Prompt Optimizer.
    """
    if not session_id:
        return ""

    conn = None
    try:
        conn = get_db()
        if not conn: return ""
        
        cursor = conn.cursor()

        # Asegúrate de incluir input_type en el SELECT
        cursor.execute(
            """
            SELECT TOP (?) role, content, input_type
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY created_at DESC
            """,
            (limit, session_id),
        )

        rows = cursor.fetchall()
        rows.reverse()  # Orden cronológico (Pasado -> Presente)

        history_lines = []
        for row in rows:
            role = "USUARIO" if row.role == "user" else "AIDA"
            text = str(row.content).replace("\n", " ").strip()
            
            # Manejo de imágenes
            if getattr(row, 'input_type', None) == "image":
                text = f"[Imagen analizada]: {text}"
            
            # Filtro anti-basura
            if "[ERROR]" in text or "mock" in text.lower():
                continue

            history_lines.append(f"{role}: {text}")

        return "\n".join(history_lines)

    except Exception as e:
        print(f"[HISTORY] Error recuperando historial: {e}")
        return ""
    
    finally:
        if conn:
            conn.close()