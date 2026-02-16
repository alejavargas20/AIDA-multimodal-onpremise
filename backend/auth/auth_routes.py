# aida-multimodal-onpremise/backend/auth/auth_routes.py
#import bcrypt



    #stored_hash = row.password_hash.encode("utf-8")

    # if not bcrypt.checkpw(data.password.encode("utf-8"), stored_hash):
    #     raise HTTPExcep   tion(status_code=401, detail="Contraseña incorrecta")

# backend/auth/auth_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pyodbc

from backend.db.connection import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])


# -----------------------------
# Schemas
# -----------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    user_id: int
    username: str
    role: str
    client_id: int | None


# -----------------------------
# Routes
# -----------------------------

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    """
    Login REAL contra SQL Server.
    (Sin hashing todavía, se hará después)
    """

    try:
        conn = get_db()
        cursor = conn.cursor()

        query = """
        SELECT
            u.user_id,
            u.username,
            u.password_hash,
            r.role_name AS role,
            u.client_id,
            u.activo
        FROM usuarios u
        JOIN roles r ON u.role_id = r.role_id
        WHERE u.username = ?
        """

        cursor.execute(query, payload.username)
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")

        if not row.activo:
            raise HTTPException(status_code=403, detail="Usuario inactivo")

        # SIN HASH POR AHORA (intencional)
        if payload.password != row.password_hash:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        return {
            "user_id": row.user_id,
            "username": row.username,
            "role": row.role,
            "client_id": row.client_id
        }

    except HTTPException:
        raise

    except Exception as e:
        print("LOGIN ERROR:", e)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass
