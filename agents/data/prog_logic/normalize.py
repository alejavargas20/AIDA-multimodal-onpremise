from __future__ import annotations
from typing import Any, Dict, List

AGG_MAP = {
    "suma": "sum",
    "sum": "sum",
    "promedio": "avg",
    "media": "avg",
    "avg": "avg",
    "min": "min",
    "max": "max",
    "count": "count_rows",
    "conteo": "count_rows",
    "count_rows": "count_rows",
    "count_distinct": "count_distinct",
    "ratio": "ratio",
    "pct_change": "pct_change",
}

PERIOD_MAP = {
    "ultimo_mes": "last_month",
    "ultimo_trimestre": "last_quarter",
    "ultimo_año": "last_year",
    "ultima_semana": "last_week",
    "ultimos_30_dias": "last_30_days",
    "ultimos_6_meses": "ultimos_6_meses",
}


def normalize_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize plan to stable internal keys."""
    print("Entra al normalize plan")
    p = dict(plan)

    metric = dict(p.get("metric") or {})
    agg = dict(metric.get("aggregation") or {})
    raw_type = (agg.get("type") or "").strip().lower()
    if raw_type:
        if raw_type not in AGG_MAP:
            raise ValueError(f"Agregación desconocida: {raw_type}")
        agg["key"] = AGG_MAP[raw_type]
    metric["aggregation"] = agg
    p["metric"] = metric

    time = dict(p.get("time") or {})
    period = dict(time.get("period") or {})
    if period.get("type") == "relative":
        val = (period.get("value") or "").strip().lower()
        if val in PERIOD_MAP:
            period["key"] = PERIOD_MAP[val]
    time["period"] = period
    p["time"] = time

    filters_out: List[Dict[str, Any]] = []
    for f in p.get("filters") or []:
        ff = dict(f)
        ff["field_norm"] = (ff.get("field") or "").strip().lower()
        filters_out.append(ff)
    p["filters"] = filters_out

    return p
