import re
from typing import Dict, Any

BLOCKED = [
    "DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE",
    "INSERT", "UPDATE", "DELETE", "MERGE",
    "EXEC", "EXECUTE", "XP_", "OPENROWSET"
]

def is_safe_sql(sql: str) -> Dict[str, Any]:
    """
    Permite:
      - DECLARE/SET/CTE (WITH) + SELECT
      - SELECT directo
    Bloquea DDL/DML y execs.
    """
    s = (sql or "").strip()
    if not s:
        return {"ok": False, "reason": "SQL vacío"}

    upper = s.upper()

    # Bloqueo por keywords peligrosas
    for kw in BLOCKED:
        if re.search(rf"\b{re.escape(kw)}\b", upper):
            return {"ok": False, "reason": f"Keyword bloqueada detectada: {kw}"}

    # Debe contener SELECT en algún punto
    if "SELECT" not in upper:
        return {"ok": False, "reason": "SQL no contiene SELECT"}

    # Control simple de multi-statement excesivo (DECLARE/SET suelen usar ;)
    # Ajusta si lo necesitas
    if upper.count(";") > 12:
        return {"ok": False, "reason": "Demasiados statements/; en SQL"}

    # Bloquear comentarios (opcional). Si quieres permitirlos, quita esto.
    if "--" in s or "/*" in s or "*/" in s:
        return {"ok": False, "reason": "Comentarios no permitidos en SQL"}

    return {"ok": True}
