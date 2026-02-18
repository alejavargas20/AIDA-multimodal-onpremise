# aida-multimodal-onpremise/agents/data/LLM_logic/prompts/sql_prompt_builder.py
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from agents.data.LLM_logic.schemas.planning import QueryPlan

_FIELD_SYNONYMS = {
    "monto": ["nMonto"],
    "monto_desembolsado": ["nMonto"],
    "plazo": ["nPlazo"],
    "producto": ["cProducto"],
    "region": ["cRegion"],
    "región": ["cRegion"],
    "oficina": ["cOficina"],
    "cliente_nuevo": ["nClienteNue"],
    "idcliente": ["idCliente"],
    "idcuenta": ["idCuenta"],
    "ncosecha": ["nCosecha"],
    "nstock": ["nStock"],
}


def _map_field_to_allowed(field_norm: str, allowed_columns: List[str]) -> Optional[str]:
    if not field_norm or not allowed_columns:
        return None

    cols_set = set(allowed_columns)

    for c in allowed_columns:
        if c.lower() == field_norm.lower():
            return c

    for cand in _FIELD_SYNONYMS.get(field_norm.lower(), []):
        if cand in cols_set:
            return cand

    token = field_norm.lower()
    candidates = [c for c in allowed_columns if token in c.lower()]
    if len(candidates) == 1:
        return candidates[0]

    return None


def _normalize_filters(filters: List[Dict[str, Any]], allowed_columns: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for f in (filters or []):
        if not isinstance(f, dict):
            continue

        field_raw = str(f.get("field") or "").strip()
        field_norm = str(f.get("field_norm") or field_raw).strip().lower()
        op = str(f.get("operator") or "=").strip()
        val = f.get("value")

        mapped = _map_field_to_allowed(field_norm, allowed_columns)

        op2 = op
        val2 = val
        if op == "=" and isinstance(val, str):
            v = val.strip()
            if not re.fullmatch(r"\d+(\.\d+)?", v) and len(v) >= 3:
                op2 = "LIKE"
                val2 = f"%{v}%"

        out.append(
            {
                "field": field_raw,
                "field_norm": field_norm,
                "mapped_column": mapped,
                "operator": op2,
                "value": val2,
                "table": f.get("table"),
            }
        )
    return out


def _examples_for_plan(plan: QueryPlan) -> str:
    shape = plan.get("result_shape", "scalar")

#     common_rules = """
# REGLAS DURAS (OBLIGATORIAS):
# - Devuelve SOLO SQL (sin markdown, sin explicación, sin comentarios).
# - NO uses DECLARE/SET/WITH: el plan ya lo resuelve.
# - NO modifiques FROM/JOIN/WHERE del plan.
# - NO inventes columnas: usa SOLO columnas permitidas por el catálogo.
# - Ratios/porcentajes:
#   - NULLIF SOLO en el DENOMINADOR: / NULLIF(denominador, 0)
#   - NO uses NULLIF en el numerador.
#   - NULLIF SIEMPRE con 2 args: NULLIF(expr, 0)
# - Si result_shape=scalar => PROHIBIDO GROUP BY.
# - Si hay GROUP BY: toda columna NO agregada del SELECT debe estar en GROUP BY.
# """.strip()
    
    common_rules = """
    REGLAS DURAS (OBLIGATORIAS):
    - Devuelve SOLO SQL (sin markdown, sin explicación, sin comentarios).
    - NO uses DECLARE/SET/WITH: el plan ya lo resuelve.
    - NO modifiques FROM/JOIN/WHERE del plan.
    - NO inventes columnas: usa SOLO columnas permitidas por el catálogo.
    - Ratios/porcentajes:
        - NULLIF SOLO en el DENOMINADOR: / NULLIF(denominador, 0)
        - NO uses NULLIF en el numerador.
        - NULLIF SIEMPRE con 2 args: NULLIF(expr, 0)
    - REGLA DE AGRUPACIÓN (VITAL): 
        - Analiza la pregunta del usuario. Si la pregunta pide datos "por mes", "cada mes", "por región", "por producto" o usa la palabra "cada" junto a una dimensión temporal/categórica, DEBES DEVOLVER UNA TABLA usando `GROUP BY` y ordenando (ORDER BY) por esa dimensión, INCLUSO SI el 'result_shape' sugerido en el JSON del plan dice 'scalar'. Eres más inteligente que el plan, corrige la forma si es necesario.
        - Si (y solo si) la pregunta NO pide agrupación ("cada", "por"), entonces obedece result_shape=scalar => PROHIBIDO GROUP BY.
        - Si hay GROUP BY: toda columna NO agregada del SELECT debe estar en GROUP BY.
    """.strip()

    scalar_examples = """
Ejemplos (scalar):
-- suma escalar
SELECT SUM(nMonto) AS Resultado
{FROM_CLAUSE}
{WHERE_CLAUSE}

-- porcentaje concentrado (escalar, SIN GROUP BY)
-- Nota: el filtro va en el CASE del numerador, NO en el WHERE.
SELECT ROUND(
  SUM(CASE WHEN cRegion LIKE '%Sur%' THEN nMonto ELSE 0 END) * 100.0
  / NULLIF(SUM(nMonto), 0),
  2
) AS Resultado
{FROM_CLAUSE}
{WHERE_CLAUSE}
""".strip()

    grouped_examples = """
Ejemplos (grouped):
SELECT cProducto, AVG(nMonto) AS Resultado
{FROM_CLAUSE}
{WHERE_CLAUSE}
GROUP BY cProducto
""".strip()

    series_examples = """
Ejemplos (series):
SELECT nCosecha, AVG(nMonto) AS Resultado
{FROM_CLAUSE}
{WHERE_CLAUSE}
GROUP BY nCosecha
ORDER BY nCosecha
""".strip()

    detail_examples = """
Ejemplos (detail):
SELECT TOP 10 *
{FROM_CLAUSE}
{WHERE_CLAUSE}
""".strip()

    if shape == "grouped":
        examples = grouped_examples
    elif shape == "series":
        examples = series_examples
    elif shape == "detail":
        examples = detail_examples
    else:
        examples = scalar_examples

    from_sql = plan.get("from_sql", "FROM <tabla>")
    where_sql = (plan.get("where_sql") or "").strip()
    where_sql = where_sql if where_sql else "-- (sin WHERE)"

    examples = examples.replace("{FROM_CLAUSE}", from_sql).replace("{WHERE_CLAUSE}", where_sql)
    return f"{common_rules}\n\n{examples}"


def build_sql_prompt(intent_or_norm: Any, plan: QueryPlan, allowed_columns: List[str]) -> str:
    if isinstance(intent_or_norm, dict) and "question" in intent_or_norm and "raw" in intent_or_norm:
        question = intent_or_norm.get("question") or "no disponible"
        inp = intent_or_norm.get("input") or {}
    else:
        raw = intent_or_norm if isinstance(intent_or_norm, dict) else {}
        question = raw.get("optimized_prompt") or raw.get("normalized_text") or "no disponible"
        tasks = (raw.get("intent_plan", {}) or {}).get("tasks") or []
        inp = tasks[0].get("input", {}) if tasks else {}

    metric = (inp.get("metric") or {})
    agg = (metric.get("aggregation") or {})
    hint_agg_type = (agg.get("key") or agg.get("type") or "unknown")
    hint_agg_type_l = str(hint_agg_type).strip().lower()

    filters = inp.get("filters") or []
    filters_norm = _normalize_filters(filters, allowed_columns)

    plan_view = {
        "result_shape": plan.get("result_shape", "scalar"),
        "from_sql": plan.get("from_sql", ""),
        "where_sql": plan.get("where_sql", ""),
        "group_by_fields": plan.get("group_by_fields", []) or [],
        "notes": plan.get("notes", ""),
        "hint_agg_type": hint_agg_type,
    }

    examples_block = _examples_for_plan(plan)

    reasoning_rules = f"""
Eres un SQL Reasoning Engine (arquitecto SQL Server).

Checklist ANTES de responder:
1) Columnas: SOLO usar columnas de ALLOWED_COLUMNS.
2) result_shape=scalar => NO GROUP BY.
3) Si hay GROUP BY: toda dimensión no agregada del SELECT debe estar en GROUP BY.
4) Ratios/porcentajes: la división debe usar NULLIF(denominador, 0).
5) Devuelve SOLO SQL.

Regla general percent/ratio (sin sobreajustar):
- Si hint_agg_type es 'percent' o 'ratio' y result_shape=scalar y existen filters:
  - NO metas filters al WHERE (no puedes cambiar el plan).
  - Implementa filters en el numerador con CASE WHEN (AND entre condiciones).
  - Denominador: total bajo el WHERE del plan.
""".strip()

    return f"""
{reasoning_rules}

Pregunta:
{question}

ALLOWED_COLUMNS (solo nombres físicos permitidos):
{json.dumps(sorted(list(set(allowed_columns))), ensure_ascii=False, indent=2)}

Plan (NO modifiques FROM/JOIN/WHERE):
{json.dumps(plan_view, ensure_ascii=False, indent=2)}

Filters estructurados (con mapping sugerido):
{json.dumps(filters_norm, ensure_ascii=False, indent=2)}

{examples_block}

Tarea:
- Genera SOLO el SELECT final (y su ORDER BY / GROUP BY si aplica).
- No incluyas DECLARE/SET/WITH: ya viene en el plan.
- Devuelve SOLO SQL. Nada más.
""".strip()
