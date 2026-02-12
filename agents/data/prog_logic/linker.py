from typing import Any, Dict, List, Optional
from agents.data.prog_logic.catalog import Catalog
from agents.data.prog_logic.aggregations import validate_aggregation_key
from dataclasses import dataclass


DEFAULT_TIME_SEM_BY_TABLE = {"desembolso": "fecha_desembolso", "cierre": "fecha_cierre"}


@dataclass(frozen=True)
class LinkedSpec:
    table: str
    agg_key: str
    metric_column: str
    metric_type: str
    date_column: Optional[str]
    date_type: Optional[str]
    where_clauses: List[str]
    rls_field: Optional[str]


def link_plan(plan: Dict[str, Any], catalog: Catalog) -> LinkedSpec:
    print("Entra al link plan")
    privacy = plan.get("privacy") or {}
    allow_sensitive = bool(privacy.get("allow_sensitive", False))

    ds = plan.get("data_sources") or []
    primary = next((x for x in ds if x.get("role") == "primary"), None)
    if not primary:
        raise ValueError("No hay data_sources.primary")
    table_name = primary["table"]
    t = catalog.table(table_name)
    schema = getattr(t, "schema", None)
    if not schema:
        raise ValueError(f"No se encontró schema para la tabla {table_name}")

    table_name = f"{table_name}"
    print("Tabla completa:", table_name)

    agg_key = (plan.get("metric") or {}).get("aggregation", {}).get("key")
    if not agg_key:
        raise ValueError("Falta metric.aggregation.key (normaliza primero)")
    validate_aggregation_key(agg_key)

    concept = ((plan.get("metric") or {}).get("concept") or "").strip().lower()
    measure_sem = concept
    if not measure_sem:
        raise ValueError(f"No hay mapping determinista para concept '{concept}'")
    metric_col = t.measures_by_sem.get(measure_sem)
    if not metric_col:
        raise ValueError(
            f"Tabla '{table_name}' no tiene measure semantic '{measure_sem}'"
        )

    if metric_col.sensitive and not allow_sensitive:
        raise ValueError(
            f"Campo sensible bloqueado por privacy: {table_name}.{metric_col.name}"
        )

    date_col = None
    date_type = None
    period = (plan.get("time") or {}).get("period") or {}
    if period.get("type") == "relative":
        sem = DEFAULT_TIME_SEM_BY_TABLE.get(table_name)
        if sem:
            dc = t.times_by_sem.get(sem)
            if dc:
                date_col = dc.name
                date_type = dc.col_type

    where: List[str] = []
    for f in plan.get("filters") or []:
        fld_norm = (f.get("field_norm") or "").lower()
        if fld_norm in ("fecha", "date"):
            continue

        col = f.get("field")
        op = f.get("operator", "=")
        val = f.get("value")
        if not col or val is None:
            continue

        if isinstance(val, str):
            val_sql = "'" + val.replace("'", "''") + "'"
        else:
            val_sql = str(val)

        ftable = f.get("table")
        if ftable and ftable != table_name:
            continue

        where.append(f"{table_name}.{col} {op} {val_sql}")

    return LinkedSpec(
        table=f"{schema}.{table_name}",
        agg_key=agg_key,
        metric_column=metric_col.name,
        metric_type=metric_col.col_type,
        date_column=date_col,
        date_type=date_type,
        where_clauses=where,
        rls_field=t.rls_field,
    )
