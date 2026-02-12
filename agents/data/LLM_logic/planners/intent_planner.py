# planners/intent_planner.py
import json
from typing import Dict, Any, List, Optional
from agents.data.LLM_logic.schemas.planning import QueryPlan

from agents.data.LLM_logic.utils import ultimo_mes_declaracion, ultimos_n_meses_where
from agents.data.LLM_logic.utils import (
    recipe_cliente__cuentas_activas,
)


def _detect_client_scope(prompt_lower: str, intent_obj: Dict[str, Any]) -> bool:
    """
    Heurística:
    - Preguntas tipo "mi ..." sugieren scope cliente
    - intent_plan.tasks[0].input.scope.type == 'cliente'
    """
    if "mi " in prompt_lower or "mi crédito" in prompt_lower or "mis " in prompt_lower:
        return True

    tasks = intent_obj.get("intent_plan", {}).get("tasks") or []
    if tasks:
        inp = tasks[0].get("input", {}) or {}
        scope = inp.get("scope", {}) or {}
        if scope.get("type") == "cliente":
            return True

    return False


def _detect_result_shape(prompt_lower: str) -> str:
    """
    scalar/grouped/series/detail
    """
    if (
        "muéstr" in prompt_lower
        or "muestr" in prompt_lower
        or "lista" in prompt_lower
        or "top " in prompt_lower
    ):
        return "detail"

    if (
        "por mes" in prompt_lower
        or "últimos" in prompt_lower
        or "ultimos" in prompt_lower
        or "evolución" in prompt_lower
        or "evolucion" in prompt_lower
    ):
        return "series"

    if (
        "por producto" in prompt_lower
        or "por oficina" in prompt_lower
        or "por región" in prompt_lower
        or "por region" in prompt_lower
        or "por tipo" in prompt_lower
        or "por " in prompt_lower
    ):
        return "grouped"

    return "scalar"


def _pick_base_table(prompt_lower: str) -> str:
    """
    Decide tabla base según keywords.
    """
    # cierre: cartera/portfolio (saldo, mora, provisiones)
    if any(
        k in prompt_lower
        for k in [
            "cartera",
            "saldo",
            "mora",
            "provision",
            "provisiones",
            "días de mora",
            "dias de mora",
        ]
    ):
        return "cartera.cierre"

    # eventos: reprogramación/condonación/cambio
    if any(k in prompt_lower for k in ["reprogram", "condon", "cambio", "evento"]):
        return "cartera.desembolso_comportamiento"

    # rcc: sistema financiero, sbs, sow
    if any(k in prompt_lower for k in ["sistema financiero", "sbs", "sow", "rcc"]):
        return "rcc.cosecha_sal"

    # default: originación
    return "cartera.desembolso"


def plan_query(intent: dict, id_cliente: Optional[int] = None) -> QueryPlan:

    prompt = intent.get("optimized_prompt", "") or ""
    prompt_lower = prompt.lower()

    # 1) client scope
    client_scope = _detect_client_scope(prompt_lower, intent)

    # 2) base table y time_field
    base = _pick_base_table(prompt_lower)
    if base == "cartera.cierre":
        time_field = "nStock"
    elif base == "cartera.desembolso_comportamiento":
        time_field = "nStock"
    else:
        time_field = "nCosecha"

    # 3) result_shape
    result_shape = _detect_result_shape(prompt_lower)

    # 4) group_by_fields sugeridos
    group_by_fields: List[str] = []
    if result_shape == "series":
        group_by_fields = [time_field]
    # grouped: el LLM suele inferir dimensión (cProducto, tipo_ope, etc.)
    # Si quieres forzarlo, puedes mapear keywords -> campo.

    # 5) periodo desde intent si viene; default ultimo_mes
    tasks = intent.get("intent_plan", {}).get("tasks") or []
    inp = tasks[0].get("input", {}) if tasks else {}
    period = (inp.get("time", {}) or {}).get("period", {}) or {}
    period_value = period.get("value", "ultimo_mes")

    # 6) Construcción determinista de preamble + from + where
    declare_sql = ""
    with_sql = ""
    from_sql = f"FROM {base}"
    where_parts: List[str] = []

    # Cliente scope: patrón cuentas activas (si no, se responde portfolio)
    if client_scope:
        # Requiere IdCliente
        if id_cliente is None:
            # No rompemos aquí: dejamos nota; el SQL fallará si no se inyecta @IdCliente.
            # (Tu orquestador puede decidir devolver error antes.)
            pass

        # Para cliente, normalmente tus queries usan cierre para determinar cuentas activas del último mes
        declare_sql = (
            (
                f"DECLARE @IdCliente INT = {int(id_cliente)};\n"
                if id_cliente is not None
                else ""
            )
            + "DECLARE @UltimoMes INT; SELECT @UltimoMes = MAX(nStock) FROM cartera.cierre;"
        )
        with_sql = recipe_cliente__cuentas_activas()

        # base para cliente: desembolso (detalles) + cuentas activas
        from_sql = "FROM cartera.desembolso d INNER JOIN CuentasActivas ca ON ca.idCuenta = d.idCuenta"
        where_parts = ["d.idCliente = @IdCliente"]

        # Nota: para preguntas de eventos (reprogram/condon) y cliente, el planner puede cambiar FROM a comportamiento.
        # Si lo quieres, se puede extender con otra receta (cuentas_activas__comportamiento).
    else:
        # Portfolio: resolver tiempo por tabla base
        if period_value == "ultimo_mes":
            declare_sql = ultimo_mes_declaracion(time_field, base)
            where_parts.append(f"{time_field} = @UltimoMes")
        else:
            # Ejemplo: ultimos_6_meses
            if "6" in str(period_value):
                decl, w = ultimos_n_meses_where(time_field, base, 6)
                declare_sql = decl
                where_parts.append(w)
            else:
                # fallback: ultimo_mes
                declare_sql = ultimo_mes_declaracion(time_field, base)
                where_parts.append(f"{time_field} = @UltimoMes")

    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    # preamble: DECLARE/SET primero, luego WITH/CTE
    preamble_sql = (
        (declare_sql + "\n" + with_sql).strip() if (declare_sql or with_sql) else ""
    )

    return {
        "base_table": base,
        "result_shape": result_shape,
        "preamble_sql": preamble_sql,
        "from_sql": from_sql.strip(),
        "where_sql": where_sql.strip(),
        "group_by_fields": group_by_fields,
        "allowed_tables": [base],
        "allowed_fields": {},
        "notes": f"time_field={time_field}, client_scope={client_scope}, period={period_value}, id_cliente={'set' if id_cliente is not None else 'none'}",
    }
