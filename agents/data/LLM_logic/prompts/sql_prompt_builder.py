# agents/data/LLM_logic/prompts/sql_prompt_builder.py
from __future__ import annotations
import json
from typing import Any, Dict, List
from agents.data.LLM_logic.schemas.planning import QueryPlan


def _examples_for_plan(plan: QueryPlan) -> str:
    shape = plan.get("result_shape", "scalar")

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
- Si result_shape=scalar => PROHIBIDO GROUP BY (debe devolver 1 fila / 1 valor).
- Si hay GROUP BY: toda columna NO agregada del SELECT debe estar en GROUP BY.
""".strip()

    scalar_examples = """
Ejemplos (scalar):
SELECT SUM(nMonto) AS Resultado
{FROM_CLAUSE}
{WHERE_CLAUSE}

-- porcentaje concentrado en una categoría (escalar, SIN GROUP BY)
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
    where_sql = plan.get("where_sql", "").strip()
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
    hint_agg_type = (agg.get("type") or agg.get("key") or "")

    plan_view = {
        "result_shape": plan.get("result_shape", "scalar"),
        "from_sql": plan.get("from_sql", ""),
        "where_sql": plan.get("where_sql", ""),
        "group_by_fields": plan.get("group_by_fields", []) or [],
        "notes": plan.get("notes", ""),
        "hint_agg_type": hint_agg_type,
    }

    examples_block = _examples_for_plan(plan)

    reasoning_rules = """
Eres un SQL Reasoning Engine (arquitecto SQL).

Checklist ANTES de responder:
1) Columnas: SOLO usar columnas de ALLOWED_COLUMNS.
2) result_shape=scalar => NO GROUP BY.
3) Si hay GROUP BY: toda dimensión no agregada del SELECT debe estar en GROUP BY.
4) Ratios: la división debe usar NULLIF(denominador, 0) y NULLIF SIEMPRE con 2 args.
5) Devuelve SOLO SQL, sin texto adicional.
""".strip()

    return f"""
{reasoning_rules}

Pregunta:
{question}

ALLOWED_COLUMNS (solo nombres físicos permitidos):
{json.dumps(sorted(list(set(allowed_columns))), ensure_ascii=False, indent=2)}

Plan (NO modifiques FROM/JOIN/WHERE):
{json.dumps(plan_view, ensure_ascii=False, indent=2)}

{examples_block}

Tarea:
- Genera SOLO el SELECT final (y su ORDER BY / GROUP BY si aplica).
- No incluyas DECLARE/SET/WITH: ya viene en el plan.
- Devuelve SOLO SQL. Nada más.
""".strip()
