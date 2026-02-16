# aida-multimodal-onpremise/backend/chat/chat_routes.py
from fastapi import APIRouter, HTTPException
from uuid import uuid4, UUID
from datetime import datetime
from backend.db.connection import get_db as get_connection
from pydantic import BaseModel

# Modelos
class FeedbackRequest(BaseModel):
    message_id: UUID
    user_id: int
    rating: int  # 1 o -1

class MessageRequest(BaseModel):
    session_id: UUID
    user_id: int
    role: str
    input_type: str
    content: str
    agent_chain: str | None = None
    latency_ms: int | None = None

class CreateSessionRequest(BaseModel):
    user_id: int

router = APIRouter(prefix="/chat", tags=["chat"])

# --- RUTAS CORREGIDAS ---

@router.post("/session")
def create_session(payload: CreateSessionRequest):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        session_id = str(uuid4())

        cursor.execute("""
            INSERT INTO chat_sessions (session_id, user_id, started_at)
            VALUES (?, ?, ?)
        """, session_id, payload.user_id, datetime.utcnow())

        conn.commit()
        return {"session_id": session_id}
    
    except Exception as e:
        print(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # ¡ESTO ES LO QUE FALTABA!
        if conn:
            conn.close()


@router.post("/message")
def save_message(payload: MessageRequest):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Usamos OUTPUT INSERTED.message_id para obtener el ID generado por SQL (NEWID())
        cursor.execute("""
            INSERT INTO chat_messages
            (session_id, user_id, role, input_type, content, agent_chain, latency_ms)
            OUTPUT INSERTED.message_id
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            str(payload.session_id),
            payload.user_id,
            payload.role,
            payload.input_type,
            payload.content,
            payload.agent_chain,
            payload.latency_ms
        )

        row = cursor.fetchone()
        if not row:
            raise Exception("No se pudo insertar el mensaje")
            
        message_id = row[0]
        conn.commit()

        return {"message_id": str(message_id)}

    except Exception as e:
        if conn: conn.rollback() # Revertir si falla
        print(f"Error saving message: {e}")
        # Retornamos error controlado o raise HTTPException
        return {"ok": False, "error": str(e)}

    finally:
        if conn:
            conn.close() # CERRAMOS SIEMPRE


@router.get("/history/{session_id}")
def get_history(session_id: str):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        rows = cursor.execute("""
            SELECT role, input_type, content, created_at
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY created_at
        """, session_id).fetchall()

        return [
            {
                "role": r[0],
                "input_type": r[1],
                "content": r[2],
                "created_at": r[3],
            }
            for r in rows
        ]
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []
    finally:
        if conn: conn.close()


@router.post("/feedback")
def save_feedback(payload: FeedbackRequest):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO message_feedback (message_id, user_id, rating)
            VALUES (?, ?, ?)
        """,
            str(payload.message_id),
            payload.user_id,
            payload.rating
        )

        conn.commit()
        return {"ok": True}

    except Exception as e:
        if conn: conn.rollback()
        print(f"Error saving feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if conn: conn.close() # Vital para evitar el bloqueo del botón


@router.get("/sessions/{user_id}")
def get_sessions(user_id: int):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        rows = cursor.execute("""
            SELECT session_id, started_at, ended_at
            FROM chat_sessions
            WHERE user_id = ?
            ORDER BY started_at DESC
        """, user_id).fetchall()

        return [
            {
                "session_id": str(r.session_id),
                "started_at": r.started_at,
                "ended_at": r.ended_at,
            }
            for r in rows
        ]
    finally:
        if conn: conn.close()



