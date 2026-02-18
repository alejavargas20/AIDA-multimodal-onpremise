# planners/intent_planner.py

from typing import Dict, Any, List, Optional, Union
from agents.data.LLM_logic.schemas.planning import QueryPlan

from agents.data.LLM_logic.utils import ultimo_mes_declaracion, ultimos_n_meses_where
from agents.data.LLM_logic.utils import recipe_cliente__cuentas_activas


NormLike = Dict[str, Any]


def _get_question(intent_or_norm: Dict[str, Any]) -> str:
    # Si viene norm: usa norm["question"]
    if "question" in intent_or_norm and "raw" in intent_or_norm:
        return intent_or_norm.get("question") or ""
    # Si viene intent raw: usa optimized_prompt o normalized_text
    return (intent_or_norm.get("optimized_prompt") or intent_or_norm.get("normalized_text") or "")


def _get_input(intent_or_norm: Dict[str, Any]) -> Dict[str, Any]:
    # Si viene norm: usa norm["input"]
    if "input" in intent_or_norm and "raw" in intent_or_norm:
        return intent_or_norm.get("input") or {}

    # Intent raw: extrae tasks[0].input
    tasks = (intent_or_norm.get("intent_plan", {}) or {}).get("tasks") or []
    return tasks[0].get("input", {}) if tasks else {}


def _detect_client_scope(prompt_lower: str, intent_raw: Dict[str, Any], input_data: Dict[str, Any]) -> bool:
    if "mi " in prompt_lower or "mi crédito" in prompt_lower or "mis " in prompt_lower:
        return True

    scope = (input_data.get("scope", {}) or {})
    if scope.get("type") == "cliente":
        return True

    # fallback por compatibilidad (si viene en raw)
    tasks = intent_raw.get("intent_plan", {}).get("tasks") or []
    if tasks:
        inp = tasks[0].get("input", {}) or {}
        scope2 = inp.get("scope", {}) or {}
        if scope2.get("type") == "cliente":
            return True

    return False


def _detect_result_shape(prompt_lower: str) -> str:
    if any(k in prompt_lower for k in ["muéstr", "muestr", "lista", "top "]):
        return "detail"

    if any(k in prompt_lower for k in ["por mes", "últimos", "ultimos", "evolución", "evolucion"]):
        return "series"

    if any(k in prompt_lower for k in ["por producto", "por oficina", "por región", "por region", "por tipo"]):
        return "grouped"

    # "por " es demasiado agresivo, lo quitamos porque genera falsos grouped
    return "scalar"


def _pick_base_table(prompt_lower: str) -> str:
    if any(k in prompt_lower for k in ["cartera", "saldo", "mora", "provision", "provisiones", "días de mora", "dias de mora"]):
        return "cartera.cierre"

    if any(k in prompt_lower for k in ["reprogram", "condon", "cambio", "evento"]):
        return "cartera.desembolso_comportamiento"

    if any(k in prompt_lower for k in ["sistema financiero", "sbs", "sow", "rcc"]):
        return "rcc.cosecha_sal"

    return "cartera.desembolso"


def _infer_period_value(input_data: Dict[str, Any]) -> str:
    time = input_data.get("time", {}) or {}
    period = time.get("period", {}) or {}

    # prefer key (si ya fue normalizado)
    if period.get("key"):
        return str(period["key"])

    # fallback al value original
    value = str(period.get("value") or "ultimo_mes")

    # Si hay filtros con hint relativo, forzamos ultimo_mes
    for f in (input_data.get("filters") or []):
        if isinstance(f, dict) and f.get("_relative_time_hint") == "ultimo_mes":
            return "ultimo_mes"

    return value


def plan_query(intent_or_norm: Dict[str, Any], id_cliente: Optional[int] = None) -> QueryPlan:
    """
    Acepta:
      - intent raw (como antes)
      - norm ({"raw","question","input","params"})

    ✅ Cambio pedido:
    - Si id_cliente viene con valor, úsalo en el WHERE también cuando NO se detecte client_scope.
    - No tocamos data_logic.py ni utils.py.
    """
    intent_raw = intent_or_norm.get("raw") if ("raw" in intent_or_norm and isinstance(intent_or_norm.get("raw"), dict)) else intent_or_norm
    input_data = _get_input(intent_or_norm)

    prompt = _get_question(intent_or_norm)
    prompt_lower = (prompt or "").lower()

    # 1) client scope
    client_scope = _detect_client_scope(prompt_lower, intent_raw, input_data)

    # 2) base table y time_field
    base = _pick_base_table(prompt_lower)
    if base in ("cartera.cierre", "cartera.desembolso_comportamiento"):
        time_field = "nStock"
    else:
        time_field = "nCosecha"

    # 3) result_shape
    result_shape = _detect_result_shape(prompt_lower)

    # 4) group_by_fields sugeridos
    group_by_fields: List[str] = []
    if result_shape == "series":
        group_by_fields = [time_field]

    # 5) periodo
    period_value = _infer_period_value(input_data)

    # 6) SQL determinista (preamble + from + where)
    declare_sql = ""
    with_sql = ""
    from_sql = f"FROM {base}"
    where_parts: List[str] = []

    if client_scope:
        # Si se pide “mi/mis” pero no hay id_cliente, bloqueamos (seguro) para no filtrar mal.
        if id_cliente is None:
            declare_sql = ""
            with_sql = ""
            from_sql = f"FROM {base}"
            where_parts = ["1=0"]
        else:
            declare_sql = (
                f"DECLARE @IdCliente INT = {int(id_cliente)};\n"
                + "DECLARE @UltimoMes INT; SELECT @UltimoMes = MAX(nStock) FROM cartera.cierre;"
            )
            with_sql = recipe_cliente__cuentas_activas()

            from_sql = "FROM cartera.desembolso d INNER JOIN CuentasActivas ca ON ca.idCuenta = d.idCuenta"
            where_parts = ["d.idCliente = @IdCliente"]

    else:
        # filtros de tiempo (como antes)
        if period_value == "ultimo_mes":
            declare_sql = ultimo_mes_declaracion(time_field, base)
            where_parts.append(f"{time_field} = @UltimoMes")
        elif "6" in period_value or "six" in period_value:
            decl, w = ultimos_n_meses_where(time_field, base, 6)
            declare_sql = decl
            where_parts.append(w)
        else:
            # fallback seguro
            declare_sql = ultimo_mes_declaracion(time_field, base)
            where_parts.append(f"{time_field} = @UltimoMes")

        # ✅ NUEVO: si data_logic te pasó id_cliente, úsalo en el WHERE
        if id_cliente is not None:
            where_parts.insert(0, f"idCliente = {int(id_cliente)}")

    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    preamble_sql = ((declare_sql + "\n" + with_sql).strip() if (declare_sql or with_sql) else "")

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
