# agents/data/LLM_logic/normalize_intent.py
from __future__ import annotations
from typing import Any, Dict, List
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


def _extract_question(payload: Dict[str, Any], raw_intent: Dict[str, Any]) -> str:
    """
    Orden de prioridad:
    1) intent.optimized_prompt
    2) payload.optimized_prompt
    3) intent.normalized_text
    4) payload.normalized_text
    5) payload.context.text   ✅ (tu caso)
    """
    q = (
        raw_intent.get("optimized_prompt")
        or payload.get("optimized_prompt")
        or raw_intent.get("normalized_text")
        or payload.get("normalized_text")
    )
    if q:
        return str(q)

    ctx = _d(payload.get("context"))
    if ctx.get("text"):
        return str(ctx["text"])

    return ""


def normalize_for_llm(payload_or_intent: Any) -> Dict[str, Any]:
    payload = _d(payload_or_intent)

    # Si llega payload del orquestador, preferimos intent_json
    raw_intent = _d(payload.get("intent_json") or payload)

    inp = _extract_primary_input(raw_intent)

    question = _extract_question(payload, raw_intent)

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

    return {
        "raw": raw_intent,
        "question": question,
        "input": input_norm,
        "params": params,
    }
