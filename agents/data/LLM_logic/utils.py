from typing import Any, Dict, Tuple
import json


def _extract_id_cliente(
    intent_json_str: str, payload_params: Dict[str, Any]
) -> int | None:
    """
    Prioridad:
    1) payload.params["IdCliente"]
    2) intent_json.intent_plan.tasks[0].input.scope.id
    3) intent_json.params.IdCliente   (si decides agregarlo al intent_json.json)
    """
    try:
        if payload_params and payload_params.get("IdCliente") is not None:
            return int(payload_params["IdCliente"])

        intent = json.loads(intent_json_str)

        tasks = intent.get("intent_plan", {}).get("tasks") or []
        if tasks:
            inp = tasks[0].get("input", {}) or {}
            scope = inp.get("scope", {}) or {}
            if scope.get("id") is not None:
                return int(scope["id"])

        intent_params = intent.get("params", {}) or {}
        if intent_params.get("IdCliente") is not None:
            return int(intent_params["IdCliente"])

        return None
    except Exception:
        return None


def yyyymm_to_date_expr(yyyymm_field: str) -> str:
    # yyyymm_field ya viene como "cartera.desembolso.nCosecha" o alias.nCosecha
    return f"DATEFROMPARTS({yyyymm_field} / 100, {yyyymm_field} % 100, 1)"


def ultimo_mes_declaracion(yyyymm_field: str, from_table: str) -> str:
    # yyyymm_field: "nCosecha" o "nStock" (sin calificar)
    return f"DECLARE @UltimoMes INT = (SELECT MAX({yyyymm_field}) FROM {from_table});"


def ultimos_n_meses_where(
    yyyymm_field: str, from_table: str, n: int
) -> Tuple[str, str]:
    # retorna (declare_sql, where_sql_fragment)
    declare = (
        "DECLARE @FechaMax DATE; "
        f"SELECT @FechaMax = MAX({yyyymm_to_date_expr(yyyymm_field)}) FROM {from_table};"
    )
    where = f"{yyyymm_to_date_expr(yyyymm_field)} >= DATEADD(MONTH, -{n-1}, @FechaMax)"
    return declare, where


def recipe_desembolso__cierre() -> str:
    return "FROM cartera.desembolso d INNER JOIN cartera.cierre c ON c.idCuenta = d.idCuenta"


def recipe_desembolso__cosecha_sal() -> str:
    return (
        "FROM cartera.desembolso d "
        "INNER JOIN rcc.cosecha_sal cs "
        "ON cs.idCliente = d.idCliente AND cs.nCosecha = d.nCosecha"
    )


def recipe_cliente__cuentas_activas() -> str:
    return (
        "WITH CuentasActivas AS ("
        "  SELECT DISTINCT idCuenta FROM cartera.cierre "
        "  WHERE idCliente = @IdCliente AND nStock = @UltimoMes"
        ") "
    )


def recipe_cuentas_activas__comportamiento() -> str:
    return (
        "FROM cartera.desembolso_comportamiento dc "
        "INNER JOIN CuentasActivas ca ON ca.idCuenta = dc.idCuentaVig"
    )


import re
from typing import Dict, Any

BLOCKED = [
    "DROP",
    "TRUNCATE",
    "ALTER",
    "CREATE",
    "GRANT",
    "REVOKE",
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "EXEC",
    "EXECUTE",
    "XP_",
    "OPENROWSET",
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
