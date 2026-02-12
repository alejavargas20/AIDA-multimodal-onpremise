# prompts/sql_prompt_builder.py

import json
from typing import Dict, Any
from agents.data.LLM_logic.schemas.planning import QueryPlan


def _examples_for_plan(plan: QueryPlan) -> str:
    """
    Devuelve micro-ejemplos (SOLO patrón SELECT) según result_shape.
    No incluye DECLARE/CTEs/JOINS porque eso lo controla el plan.
    """
    shape = plan.get("result_shape", "scalar")

    common_rules = """
- NO uses DECLARE/SET/WITH. Eso ya está resuelto por el plan.
- Genera únicamente el SELECT final (+ GROUP BY/ORDER BY si aplica).    
Reglas de estilo (obligatorias):
- Devuelve SOLO SQL (sin markdown, sin explicación).
- NO cambies el FROM/JOIN/WHERE del plan.
- No inventes columnas.
- Usa alias AS Resultado cuando sea una sola métrica escalar.
- Para ratios/porcentajes usa NULLIF para evitar división por cero.
""".strip()

    # Ejemplos mínimos, centrados en SELECT + GROUP BY + ORDER BY
    scalar_examples = """
Micro-ejemplos (scalar):
SELECT SUM(nMonto) AS Resultado
{FROM_CLAUSE}
{WHERE_CLAUSE}

SELECT COUNT(*) AS Resultado
{FROM_CLAUSE}
{WHERE_CLAUSE}

-- porcentaje (solo si la pregunta pide porcentaje/ratio)
SELECT ROUND(
  SUM(CASE WHEN nMora > 0 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0),
  2
) AS Resultado
{FROM_CLAUSE}
{WHERE_CLAUSE}
""".strip()

    grouped_examples = """
Micro-ejemplos (grouped):
SELECT cProducto, AVG(nMonto) AS Resultado
{FROM_CLAUSE}
{WHERE_CLAUSE}
GROUP BY cProducto

-- porcentaje por grupo (solo si aplica)
SELECT cProducto,
  ROUND(
    SUM(CASE WHEN nMora > 0 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0),
    2
  ) AS Resultado
{FROM_CLAUSE}
{WHERE_CLAUSE}
GROUP BY cProducto
""".strip()

    series_examples = """
Micro-ejemplos (series):
SELECT nStock, COUNT(*) AS Resultado
{FROM_CLAUSE}
{WHERE_CLAUSE}
GROUP BY nStock
ORDER BY nStock

SELECT nCosecha, AVG(nMonto) AS Resultado
{FROM_CLAUSE}
{WHERE_CLAUSE}
GROUP BY nCosecha
ORDER BY nCosecha
""".strip()

    detail_examples = """
Micro-ejemplos (detail):
SELECT TOP 1 nMonto
{FROM_CLAUSE}
{WHERE_CLAUSE}
ORDER BY nCosecha DESC
""".strip()

    # Elegir bloque según shape
    if shape == "grouped":
        examples = grouped_examples
    elif shape == "series":
        examples = series_examples
    elif shape == "detail":
        examples = detail_examples
    else:
        examples = scalar_examples

    # Insertar placeholders con el FROM/WHERE del plan como referencia de forma
    from_sql = plan.get("from_sql", "FROM <tabla>")
    where_sql = plan.get("where_sql", "").strip()
    where_sql = where_sql if where_sql else "-- (sin WHERE)"

    examples = examples.replace("{FROM_CLAUSE}", from_sql).replace(
        "{WHERE_CLAUSE}", where_sql
    )

    return f"{common_rules}\n\n{examples}"


def build_sql_prompt(intent: str, plan: QueryPlan) -> str:
    """
    Prompt optimizado:
    - Plan determinista manda FROM/JOIN/WHERE.
    - Ejemplos dinámicos según result_shape.
    - LLM solo debe completar SELECT (+ GROUP BY/ORDER BY si corresponde).
    """
    question = intent.get("optimized_prompt", "no disponible")

    # Campos útiles del plan
    result_shape = plan.get("result_shape", "scalar")
    group_by_fields = plan.get("group_by_fields", []) or []

    plan_view = {
        "result_shape": result_shape,
        "from_sql": plan.get("from_sql", ""),
        "where_sql": plan.get("where_sql", ""),
        "group_by_fields": group_by_fields,
        "notes": plan.get("notes", ""),
    }

    examples_block = _examples_for_plan(plan)

    # Instrucciones directas y cortas
    return f"""
Eres un experto en SQL Server para analítica de créditos.
Devuelve SOLO SQL (sin markdown, sin explicación, sin comentarios).

Pregunta:
{question}

Plan (NO modifiques FROM/JOIN/WHERE):
{json.dumps(plan_view, ensure_ascii=False, indent=2)}

Instrucción principal:
- Escribe el SELECT final que responda la pregunta.
- Si result_shape es:
  - scalar: una sola fila con una métrica.
  - grouped: incluir GROUP BY usando las dimensiones requeridas.
  - series: agrupar por el campo temporal y ORDER BY ascendente.
  - detail: devolver filas detalladas (TOP si corresponde).

{examples_block}

Ahora genera SOLO el SQL final.
""".strip()
