#aida-multimodal-onpremise/agents/data/prog_logic/aggregations.py

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class AggregationSpec:
    key: str
    valid_for_types: List[str]  # simplified types: int/float/numeric/date/datetime/any
    requires_field: bool = True


AGGREGATIONS: Dict[str, AggregationSpec] = {
    "sum": AggregationSpec("sum", ["int", "float", "numeric"], True),
    "avg": AggregationSpec("avg", ["int", "float", "numeric"], True),
    "min": AggregationSpec(
        "min", ["int", "float", "numeric", "date", "datetime"], True
    ),
    "max": AggregationSpec(
        "max", ["int", "float", "numeric", "date", "datetime"], True
    ),
    "count_rows": AggregationSpec("count_rows", ["any"], False),
    "count_distinct": AggregationSpec("count_distinct", ["any"], True),
    "ratio": AggregationSpec("ratio", ["numeric"], False),
    "pct_change": AggregationSpec("pct_change", ["numeric"], False),
}


def normalize_type(t: str) -> str:
    tt = (t or "").lower()
    if any(x in tt for x in ["int", "bigint", "smallint", "tinyint"]):
        return "int"
    if any(x in tt for x in ["float", "double", "real"]):
        return "float"
    if any(x in tt for x in ["decimal", "numeric", "money"]):
        return "numeric"
    if "datetime" in tt or "timestamp" in tt:
        return "datetime"
    if "date" in tt and "datetime" not in tt:
        return "date"
    return "any"


def validate_aggregation_key(agg_key: str) -> None:
    if agg_key not in AGGREGATIONS:
        raise ValueError(f"Agregación no soportada: {agg_key}")


def validate_aggregation_for_field(agg_key: str, field_type: str) -> None:
    validate_aggregation_key(agg_key)
    spec = AGGREGATIONS[agg_key]
    tnorm = normalize_type(field_type)

    if "any" in spec.valid_for_types:
        return

    if agg_key in ("ratio", "pct_change"):
        if tnorm not in ("int", "float", "numeric"):
            raise ValueError(
                f"{agg_key} requiere tipo numérico; recibido: {field_type} ({tnorm})"
            )
        return

    if tnorm not in spec.valid_for_types:
        raise ValueError(
            f"Agregación '{agg_key}' no válida para tipo {field_type} ({tnorm})."
        )


def render_simple_agg_mssql(
    agg_key: str,
    table: str,
    field: Optional[str],
    field_type: str,
    *,
    distinct_field: Optional[str] = None,
) -> str:
    """Render SUM/AVG/MIN/MAX/COUNT for SQL Server."""
    validate_aggregation_key(agg_key)

    if agg_key == "count_rows":
        return "COUNT(1)"

    if agg_key == "count_distinct":
        if not distinct_field:
            raise ValueError("count_distinct requiere distinct_field")
        return f"COUNT(DISTINCT {table}.{distinct_field})"

    if not field:
        raise ValueError(f"Agregación '{agg_key}' requiere un field")

    validate_aggregation_for_field(agg_key, field_type)

    fn = {"sum": "SUM", "avg": "AVG", "min": "MIN", "max": "MAX"}[agg_key]
    return f"{fn}({table}.{field})"


def render_ratio_mssql(numerator_sql: str, denominator_sql: str) -> str:
    # Evita división por cero
    return f"({numerator_sql} / NULLIF({denominator_sql}, 0))"


def render_pct_change_mssql(current_sql: str, previous_sql: str) -> str:
    # (current - previous) / previous
    return f"(({current_sql} - {previous_sql}) / NULLIF({previous_sql}, 0))"
