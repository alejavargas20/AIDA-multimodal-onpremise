from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, List

from .linker import LinkedSpec
from .dialect import expr_period_start_relative
from .aggregations import (
    render_simple_agg_mssql,
    render_ratio_mssql,
    render_pct_change_mssql,
)


# ---------------------------------------------------------------------
# Base Template
# ---------------------------------------------------------------------
@dataclass
class Template:
    name: str
    description: str

    def matches(self, plan: Dict[str, Any], spec: LinkedSpec) -> bool:
        raise NotImplementedError

    def render(self, plan: Dict[str, Any], spec: LinkedSpec) -> str:
        raise NotImplementedError


# ---------------------------------------------------------------------
# Helpers comunes (DRY)
# ---------------------------------------------------------------------
def _get_time(plan: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    time = plan.get("time") or {}
    period = time.get("period") or {}
    gran = (time.get("granularity") or "").strip().lower()
    return time, period, gran


def _get_period_key(period: Dict[str, Any]) -> str:
    # usa key preferente, fallback a value por compat
    return (period.get("value") or "").strip()


def _build_where_relative(plan: Dict[str, Any], spec: LinkedSpec) -> str:
    _, period, _ = _get_time(plan)
    period_key = _get_period_key(period)
    if not spec.date_column:
        raise ValueError("Requiere date_column linkeada para filtros temporales.")
    if not period_key:
        raise ValueError("Falta time.period.key/value (normaliza primero).")

    start_expr = expr_period_start_relative(period_key)
    where = [f"{spec.table}.{spec.date_column} >= {start_expr}"]
    where.extend(spec.where_clauses)
    return " AND ".join(where) if where else "1=1"


def _grouping_sql(tbl: str, date_col: str, gran: str) -> Tuple[str, str, str]:
    """
    Devuelve (select_group, group_by, order_by)
    """
    if gran == "mensual":
        select_group = (
            f"YEAR({tbl}.{date_col}) AS anio,\n  MONTH({tbl}.{date_col}) AS mes"
        )
        group_by = f"YEAR({tbl}.{date_col}), MONTH({tbl}.{date_col})"
        order_by = "anio, mes"
        return select_group, group_by, order_by

    if gran == "diaria":
        d = f"CAST({tbl}.{date_col} AS date)"
        select_group = f"{d} AS fecha"
        group_by = d
        order_by = "fecha"
        return select_group, group_by, order_by

    raise ValueError(f"Granularidad no soportada: {gran}")


def _render_metric_agg(spec: LinkedSpec) -> str:
    """
    Render para sum/avg/min/max sobre la métrica linkeada en spec.
    """
    return render_simple_agg_mssql(
        agg_key=spec.agg_key,
        table=spec.table,
        field=spec.metric_column,
        field_type=spec.metric_type,
    )


def _render_count_rows(spec: LinkedSpec) -> str:
    return render_simple_agg_mssql(
        agg_key="count_rows",
        table=spec.table,
        field=None,
        field_type="any",
    )


def _render_count_distinct(plan: Dict[str, Any], spec: LinkedSpec) -> str:
    grain = ((plan.get("entity") or {}).get("grain") or "").strip()
    if not grain:
        raise ValueError(
            "count_distinct requiere entity.grain (ej: idCuenta, idSolicitud)."
        )
    return render_simple_agg_mssql(
        agg_key="count_distinct",
        table=spec.table,
        field=grain,
        field_type="any",
        distinct_field=grain,
    )


# ---------------------------------------------------------------------
# 1) Agregación simple + relativo + sin granularidad (sum/avg/min/max)
# ---------------------------------------------------------------------
class MetricAggRelativeNoGroupBy(Template):
    def matches(self, plan: Dict[str, Any], spec: LinkedSpec) -> bool:
        _, period, gran = _get_time(plan)
        return (
            period.get("type") == "relative"
            and (gran == "" or gran is None)
            and spec.agg_key in ("sum", "avg", "min", "max")
        )

    def render(self, plan: Dict[str, Any], spec: LinkedSpec) -> str:
        print("Entra aqui")
        tbl = spec.table
        where_sql = _build_where_relative(plan, spec)
        print(where_sql)
        agg_sql = _render_metric_agg(spec)
        print(agg_sql)
        return f"""SELECT
            {agg_sql} AS valor
            FROM {tbl}
            WHERE {where_sql}"""


# ---------------------------------------------------------------------
# 2) Agregación simple + relativo + granularidad (diaria/mensual)
# ---------------------------------------------------------------------
class MetricAggRelativeWithGranularity(Template):
    def matches(self, plan: Dict[str, Any], spec: LinkedSpec) -> bool:
        _, period, gran = _get_time(plan)
        return (
            period.get("type") == "relative"
            and gran in ("mensual", "diaria")
            and spec.agg_key in ("sum", "avg", "min", "max")
        )

    def render(self, plan: Dict[str, Any], spec: LinkedSpec) -> str:
        if not spec.date_column:
            raise ValueError("Requiere date_column linkeada.")
        tbl = spec.table
        where_sql = _build_where_relative(plan, spec)
        agg_sql = _render_metric_agg(spec)

        _, _, gran = _get_time(plan)
        select_group, group_by, order_by = _grouping_sql(tbl, spec.date_column, gran)

        return f"""SELECT
  {select_group},
  {agg_sql} AS valor
FROM {tbl}
WHERE {where_sql}
GROUP BY {group_by}
ORDER BY {order_by}"""


# ---------------------------------------------------------------------
# 3) COUNT_ROWS + relativo (con o sin granularidad)
# ---------------------------------------------------------------------
class CountRowsRelative(Template):
    def matches(self, plan: Dict[str, Any], spec: LinkedSpec) -> bool:
        _, period, gran = _get_time(plan)
        return (
            period.get("type") == "relative"
            and spec.agg_key == "count_rows"
            and gran in ("", None, "mensual", "diaria")
        )

    def render(self, plan: Dict[str, Any], spec: LinkedSpec) -> str:
        tbl = spec.table
        where_sql = _build_where_relative(plan, spec)
        agg_sql = _render_count_rows(spec)

        _, _, gran = _get_time(plan)
        if gran in ("", None):
            return f"""SELECT
  {agg_sql} AS valor
FROM {tbl}
WHERE {where_sql}"""

        if not spec.date_column:
            raise ValueError("Requiere date_column linkeada para granularidad.")
        select_group, group_by, order_by = _grouping_sql(tbl, spec.date_column, gran)
        return f"""SELECT
  {select_group},
  {agg_sql} AS valor
FROM {tbl}
WHERE {where_sql}
GROUP BY {group_by}
ORDER BY {order_by}"""


# ---------------------------------------------------------------------
# 4) COUNT_DISTINCT(grain) + relativo (con o sin granularidad)
# ---------------------------------------------------------------------
class CountDistinctRelative(Template):
    def matches(self, plan: Dict[str, Any], spec: LinkedSpec) -> bool:
        _, period, gran = _get_time(plan)
        return (
            period.get("type") == "relative"
            and spec.agg_key == "count_distinct"
            and gran in ("", None, "mensual", "diaria")
        )

    def render(self, plan: Dict[str, Any], spec: LinkedSpec) -> str:
        tbl = spec.table
        where_sql = _build_where_relative(plan, spec)
        agg_sql = _render_count_distinct(plan, spec)

        _, _, gran = _get_time(plan)
        if gran in ("", None):
            return f"""SELECT
  {agg_sql} AS valor
FROM {tbl}
WHERE {where_sql}"""

        if not spec.date_column:
            raise ValueError("Requiere date_column linkeada para granularidad.")
        select_group, group_by, order_by = _grouping_sql(tbl, spec.date_column, gran)
        return f"""SELECT
  {select_group},
  {agg_sql} AS valor
FROM {tbl}
WHERE {where_sql}
GROUP BY {group_by}
ORDER BY {order_by}"""


# ---------------------------------------------------------------------
# 5) RATIO (numerador/denominador) + relativo (con o sin granularidad)
# ---------------------------------------------------------------------
class RatioRelative(Template):
    """
    Espera que el plan traiga:
      plan["metric"]["aggregation"]["numerator"] = { "agg_key": "sum"/... , "concept": "..."}  (o algo equivalente)
      plan["metric"]["aggregation"]["denominator"] = { "agg_key": "count_distinct"/... , "field": "id..." / "concept": "..."}
    Y que tu linker haya resuelto:
      spec.submetrics["numerator"] = (agg_key, column, type, distinct_field?)
      spec.submetrics["denominator"] = ...
    Si aún no tienes submetrics en LinkedSpec, necesitas extender el linker.
    """

    def matches(self, plan: Dict[str, Any], spec: LinkedSpec) -> bool:
        _, period, gran = _get_time(plan)
        agg = (plan.get("metric") or {}).get("aggregation") or {}
        return (
            period.get("type") == "relative"
            and spec.agg_key == "ratio"
            and agg.get("numerator") is not None
            and agg.get("denominator") is not None
            and gran in ("", None, "mensual", "diaria")
        )

    def render(self, plan: Dict[str, Any], spec: LinkedSpec) -> str:
        if not hasattr(spec, "submetrics") or not spec.submetrics:
            raise ValueError(
                "Ratio requiere spec.submetrics (extiende el linker para numerador/denominador)."
            )

        tbl = spec.table
        where_sql = _build_where_relative(plan, spec)

        num = spec.submetrics["numerator"]
        den = spec.submetrics["denominator"]

        num_sql = render_simple_agg_mssql(
            num["agg_key"],
            tbl,
            num.get("field"),
            num.get("field_type", "any"),
            distinct_field=num.get("distinct_field"),
        )
        den_sql = render_simple_agg_mssql(
            den["agg_key"],
            tbl,
            den.get("field"),
            den.get("field_type", "any"),
            distinct_field=den.get("distinct_field"),
        )

        ratio_sql = render_ratio_mssql(num_sql, den_sql)

        _, _, gran = _get_time(plan)
        if gran in ("", None):
            return f"""SELECT
  {ratio_sql} AS valor
FROM {tbl}
WHERE {where_sql}"""

        if not spec.date_column:
            raise ValueError("Requiere date_column linkeada para granularidad.")
        select_group, group_by, order_by = _grouping_sql(tbl, spec.date_column, gran)

        return f"""SELECT
  {select_group},
  {ratio_sql} AS valor
FROM {tbl}
WHERE {where_sql}
GROUP BY {group_by}
ORDER BY {order_by}"""


# ---------------------------------------------------------------------
# 6) PCT_CHANGE vs periodo anterior + relativo (con o sin granularidad)
# ---------------------------------------------------------------------
class PctChangeRelativeVsPrevious(Template):
    """
    Requiere:
      plan["comparison"]["enabled"] = True
      plan["comparison"]["type"] = "previous_period"
      spec.agg_key == "pct_change"
    Implementación: dos CTEs (current y previous) y luego pct_change.
    """

    def matches(self, plan: Dict[str, Any], spec: LinkedSpec) -> bool:
        _, period, gran = _get_time(plan)
        comp = plan.get("comparison") or {}
        return (
            period.get("type") == "relative"
            and spec.agg_key == "pct_change"
            and comp.get("enabled") is True
            and comp.get("type") == "previous_period"
            and gran in ("", None, "mensual", "diaria")
        )

    def render(self, plan: Dict[str, Any], spec: LinkedSpec) -> str:
        if not spec.date_column:
            raise ValueError("pct_change requiere date_column linkeada.")
        tbl = spec.table

        # current window start
        _, period, gran = _get_time(plan)
        period_key = _get_period_key(period)
        start_expr = expr_period_start_relative(period_key)

        # previous window start: desplazamos el mismo tamaño hacia atrás.
        # Esto depende de cómo definas period_key. Aquí hacemos un mapeo simple.
        # Si quieres exactitud, implementa una función period_prev_start(period_key).
        prev_start_expr = expr_period_start_relative(f"prev_{period_key}")

        base_where_extra = (
            " AND ".join(spec.where_clauses) if spec.where_clauses else "1=1"
        )

        # current aggregate
        curr_agg = _render_metric_agg(spec)
        prev_agg = _render_metric_agg(spec)

        if gran in ("", None):
            return f"""WITH current_period AS (
  SELECT {curr_agg} AS v
  FROM {tbl}
  WHERE {tbl}.{spec.date_column} >= {start_expr} AND {base_where_extra}
),
previous_period AS (
  SELECT {prev_agg} AS v
  FROM {tbl}
  WHERE {tbl}.{spec.date_column} >= {prev_start_expr} AND {tbl}.{spec.date_column} < {start_expr} AND {base_where_extra}
)
SELECT
  {render_pct_change_mssql("current_period.v", "previous_period.v")} AS valor
FROM current_period
CROSS JOIN previous_period"""

        # Granularidad: CTEs con agrupación
        select_group, group_by, order_by = _grouping_sql(tbl, spec.date_column, gran)

        # Para mensual/diaria el "previous" debería alinear por bucket; esto lo resolvemos con join por bucket.
        # (Mensual: (anio,mes); Diaria: fecha)
        if gran == "mensual":
            bucket_select = f"YEAR({tbl}.{spec.date_column}) AS anio, MONTH({tbl}.{spec.date_column}) AS mes"
            bucket_join = "c.anio = p.anio AND c.mes = p.mes"
            bucket_cols = "anio, mes"
        else:
            bucket_select = f"CAST({tbl}.{spec.date_column} AS date) AS fecha"
            bucket_join = "c.fecha = p.fecha"
            bucket_cols = "fecha"

        return f"""WITH current_period AS (
  SELECT
    {bucket_select},
    {curr_agg} AS v
  FROM {tbl}
  WHERE {tbl}.{spec.date_column} >= {start_expr} AND {base_where_extra}
  GROUP BY {group_by}
),
previous_period AS (
  SELECT
    {bucket_select},
    {prev_agg} AS v
  FROM {tbl}
  WHERE {tbl}.{spec.date_column} >= {prev_start_expr} AND {tbl}.{spec.date_column} < {start_expr} AND {base_where_extra}
  GROUP BY {group_by}
)
SELECT
  c.{bucket_cols},
  {render_pct_change_mssql("c.v", "p.v")} AS valor
FROM current_period c
LEFT JOIN previous_period p
  ON {bucket_join}
ORDER BY {order_by}"""


# ---------------------------------------------------------------------
# 7) TOP-N por dimensión (ranking) + relativo
# ---------------------------------------------------------------------
class TopNByDimensionRelative(Template):
    """
    Requiere:
      plan["group_by"] = {"field": "<dimension_field>"}  (o equivalente)
      plan["limit"] = N
      spec.agg_key in (sum/avg/min/max/count_rows/count_distinct)
    """

    def matches(self, plan: Dict[str, Any], spec: LinkedSpec) -> bool:
        _, period, gran = _get_time(plan)
        group_by = plan.get("group_by") or {}
        limit = plan.get("limit")
        return (
            period.get("type") == "relative"
            and (gran == "" or gran is None)  # topN típico sin granularidad temporal
            and group_by.get("field")
            and isinstance(limit, int)
            and limit > 0
            and spec.agg_key
            in ("sum", "avg", "min", "max", "count_rows", "count_distinct")
        )

    def render(self, plan: Dict[str, Any], spec: LinkedSpec) -> str:
        tbl = spec.table
        where_sql = _build_where_relative(plan, spec)

        group_field = (plan.get("group_by") or {}).get("field")
        limit = int(plan.get("limit"))

        # agg SQL
        if spec.agg_key in ("count_rows",):
            agg_sql = _render_count_rows(spec)
        elif spec.agg_key in ("count_distinct",):
            agg_sql = _render_count_distinct(plan, spec)
        else:
            agg_sql = _render_metric_agg(spec)

        return f"""SELECT TOP ({limit})
  {tbl}.{group_field} AS dimension,
  {agg_sql} AS valor
FROM {tbl}
WHERE {where_sql}
GROUP BY {tbl}.{group_field}
ORDER BY valor DESC"""


# ---------------------------------------------------------------------
# 8) Multi-table JOIN (shape) + relativo (placeholder realista)
# ---------------------------------------------------------------------
class MultiTableJoinRelative(Template):
    """
    Shape para consultas que requieren múltiples tablas en data_sources.
    Requiere que tu linker construya spec.joins = [ "JOIN ... ON ..." ] y que
    resuelva columnas con prefijo correcto.

    matches: si hay >1 data_source
    """

    def matches(self, plan: Dict[str, Any], spec: LinkedSpec) -> bool:
        ds = plan.get("data_sources") or []
        _, period, gran = _get_time(plan)
        return (
            period.get("type") == "relative" and len(ds) > 1 and hasattr(spec, "joins")
        )

    def render(self, plan: Dict[str, Any], spec: LinkedSpec) -> str:
        if not hasattr(spec, "joins"):
            raise ValueError(
                "MultiTableJoinRelative requiere spec.joins (extiende el linker)."
            )

        tbl = spec.table
        join_sql = "\n".join(spec.joins)
        where_sql = _build_where_relative(plan, spec)

        # Por defecto usamos métrica simple (puedes especializar por agg_key)
        if spec.agg_key in ("count_rows",):
            agg_sql = _render_count_rows(spec)
        elif spec.agg_key in ("count_distinct",):
            agg_sql = _render_count_distinct(plan, spec)
        else:
            agg_sql = _render_metric_agg(spec)

        return f"""SELECT
  {agg_sql} AS valor
FROM {tbl}
{join_sql}
WHERE {where_sql}"""
