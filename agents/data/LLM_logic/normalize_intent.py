# agents/data/LLM_logic/normalize_intent.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple
import re

AGG_MAP = {
    "suma": "sum", "sum": "sum", "total": "sum",
    "avg": "avg", "promedio": "avg", "mean": "avg",
    "count": "count", "conteo": "count", "cantidad": "count",
    "count_distinct": "count_distinct", "distinct": "count_distinct",
    "ratio": "ratio",
    "percent": "percent", "porcentaje": "percent",
}

PERIOD_MAP = {
    "ultimo_mes": "ultimo_mes", "último_mes": "ultimo_mes", "last_month": "ultimo_mes",
    "ultimo_6_meses": "ultimo_6_meses", "ultimos_6_meses": "ultimo_6_meses",
    "últimos_6_meses": "ultimo_6_meses",
    "ultimo_six_months": "ultimo_6_meses", "ultimos_six_months": "ultimo_6_meses",
}

NOW_MINUS_MONTH_PATTERNS = [
    r"now\(\)\s*-\s*1\s*month",
    r"current_timestamp\s*-\s*interval\s*'1\s*month'",
    r"getdate\(\)\s*-\s*(30|31)",
]


def _d(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _extract_primary_input(intent_obj: Dict[str, Any]) -> Dict[str, Any]:
    tasks = (intent_obj.get("intent_plan", {}) or {}).get("tasks") or []
    if tasks:
        return tasks[0].get("input", {}) or {}
    return intent_obj


def _looks_like_sql(text: str) -> bool:
    if not text:
        return False
    t = text.strip().lower()
    return (
        t.startswith("select")
        or t.startswith("declare")
        or " from " in f" {t} "
        or " where " in f" {t} "
    )


def _extract_question_and_source(payload: Dict[str, Any], raw_intent: Dict[str, Any]) -> Tuple[str, str]:
    """
    SOLO mira campos del intent/payload (NO metadata).
    Si viene payload recortado (input-only), normalmente no habrá question
    y se reconstruirá más abajo.
    """
    candidates = [
        ("intent.optimized_prompt", raw_intent.get("optimized_prompt")),
        ("payload.optimized_prompt", payload.get("optimized_prompt")),
        ("intent.normalized_text", raw_intent.get("normalized_text")),
        ("payload.normalized_text", payload.get("normalized_text")),
        ("payload.context.text", _d(payload.get("context")).get("text")),
        ("intent.user_text", raw_intent.get("user_text")),
        ("payload.user_text", payload.get("user_text")),
        ("intent.text", raw_intent.get("text")),
        ("payload.text", payload.get("text")),
    ]

    for src, val in candidates:
        if not val:
            continue
        q = str(val).strip()
        if not q:
            continue
        if _looks_like_sql(q):
            continue
        return q, src

    return "", "none"


def _reconstruct_question_from_input(input_norm: Dict[str, Any]) -> str:
    """
    Reconstrucción mínima y general desde input estructurado.
    No es “bonita”, pero le da contexto al LLM sin depender del optimizer.
    """
    metric = input_norm.get("metric") or {}
    agg = (metric.get("aggregation") or {})
    agg_key = (agg.get("key") or agg.get("type") or "unknown").strip().lower()

    time = input_norm.get("time") or {}
    period = (time.get("period") or {})
    period_key = (period.get("key") or period.get("value") or "").strip().lower()

    filters = input_norm.get("filters") or []

    if agg_key in ("ratio", "percent"):
        head = "¿Qué porcentaje del monto desembolsado"
    elif agg_key == "avg":
        head = "¿Cuál es el monto promedio desembolsado"
    elif agg_key == "count":
        head = "¿Cuántos créditos se desembolsaron"
    else:
        head = "¿Cuál fue el monto total desembolsado"

    tail = ""
    if period_key == "ultimo_mes":
        tail = " en el último mes"
    elif "6" in period_key:
        tail = " en los últimos 6 meses"

    # Solo añadimos una pista textual de filtro (sin sobreajustar)
    filt_txt = ""
    if filters:
        parts = []
        for f in filters:
            if not isinstance(f, dict):
                continue
            fld = f.get("field") or f.get("field_norm")
            val = f.get("value")
            if fld and val is not None:
                parts.append(f"{fld}={val}")
        if parts:
            filt_txt = " con filtros " + ", ".join(parts)

    return f"{head}{tail}{filt_txt}?"


def normalize_for_llm(payload_or_intent: Any) -> Dict[str, Any]:
    payload = _d(payload_or_intent)

    # Preferimos intent_json si existe, si no, payload
    raw_intent = _d(payload.get("intent_json") or payload)

    inp = _extract_primary_input(raw_intent)

    question, question_source = _extract_question_and_source(payload, raw_intent)

    # Params merge (payload tiene prioridad)
    params: Dict[str, Any] = {}
    params.update(_d(raw_intent.get("params")))
    params.update(_d(payload.get("params")))

    # Normalizar metric/agg
    metric = dict(inp.get("metric") or {})
    agg = dict(metric.get("aggregation") or {})
    raw_agg_type = (agg.get("type") or "").strip().lower()
    agg["key"] = AGG_MAP.get(raw_agg_type, raw_agg_type or "unknown")
    metric["aggregation"] = agg

    # Normalizar time/period
    time = dict(inp.get("time") or {})
    period = dict(time.get("period") or {})
    if (period.get("type") or "").lower() == "relative":
        v = (period.get("value") or "").strip().lower()
        period["key"] = PERIOD_MAP.get(v, v or "ultimo_mes")
    time["period"] = period

    # Normalizar filtros
    filters_out: List[Dict[str, Any]] = []
    for f in (inp.get("filters") or []):
        ff = dict(f)
        ff["field_norm"] = (ff.get("field") or "").strip().lower()

        val = str(ff.get("value") or "").strip().lower()
        if any(re.search(pat, val) for pat in NOW_MINUS_MONTH_PATTERNS):
            ff["_relative_time_hint"] = "ultimo_mes"

        filters_out.append(ff)

    input_norm = dict(inp)
    input_norm["metric"] = metric
    input_norm["time"] = time
    input_norm["filters"] = filters_out

    # ✅ si no hay question, reconstruimos desde input_norm (sin metadata)
    if not question:
        question = _reconstruct_question_from_input(input_norm)
        question_source = "reconstructed_from_input"

    return {
        "raw": raw_intent,
        "question": question,
        "question_source": question_source,
        "input": input_norm,
        "params": params,
    }
