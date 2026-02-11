from typing import Any, Dict, List

from agents.data.prog_logic.linker import LinkedSpec
from agents.data.prog_logic.template import (
    Template,
    # Agregaciones simples
    MetricAggRelativeNoGroupBy,
    MetricAggRelativeWithGranularity,
    # Conteos
    CountRowsRelative,
    CountDistinctRelative,
    # Ratio y variación
    RatioRelative,
    PctChangeRelativeVsPrevious,
    # Rankings
    TopNByDimensionRelative,
    # Joins
    MultiTableJoinRelative,
)


_TEMPLATES: List[Template] = [
    # ------------------------------------------------------------------
    # 1) MULTI-TABLA (joins)
    # ------------------------------------------------------------------
    MultiTableJoinRelative(
        name="multi_table_join_relative",
        description="Consultas con múltiples tablas usando joins (periodo relativo).",
    ),
    # ------------------------------------------------------------------
    # 2) VARIACIÓN % VS PERIODO ANTERIOR
    # ------------------------------------------------------------------
    PctChangeRelativeVsPrevious(
        name="pct_change_relative_vs_previous",
        description="Cambio porcentual vs periodo anterior (pct_change).",
    ),
    # ------------------------------------------------------------------
    # 3) RATIO (numerador / denominador)
    # ------------------------------------------------------------------
    RatioRelative(
        name="ratio_relative",
        description="Ratio entre dos métricas agregadas (numerador/denominador).",
    ),
    # ------------------------------------------------------------------
    # 4) TOP-N / RANKING
    # ------------------------------------------------------------------
    TopNByDimensionRelative(
        name="topn_by_dimension_relative",
        description="Top-N por dimensión en periodo relativo.",
    ),
    # ------------------------------------------------------------------
    # 5) COUNT DISTINCT (usando entity.grain)
    # ------------------------------------------------------------------
    CountDistinctRelative(
        name="count_distinct_relative",
        description="COUNT DISTINCT(grain) en periodo relativo (con o sin granularidad).",
    ),
    # ------------------------------------------------------------------
    # 6) COUNT ROWS
    # ------------------------------------------------------------------
    CountRowsRelative(
        name="count_rows_relative",
        description="COUNT ROWS en periodo relativo (con o sin granularidad).",
    ),
    # ------------------------------------------------------------------
    # 7) AGREGACIONES SIMPLES CON GRANULARIDAD
    #    (sum / avg / min / max + diaria o mensual)
    # ------------------------------------------------------------------
    MetricAggRelativeWithGranularity(
        name="metric_relative_groupby",
        description="Agregación simple sobre tabla primaria en periodo relativo (con group by).",
    ),
    # ------------------------------------------------------------------
    # 8) AGREGACIONES SIMPLES SIN GRANULARIDAD
    #    (sum / avg / min / max)
    # ------------------------------------------------------------------
    MetricAggRelativeNoGroupBy(
        name="metric_relative_no_groupby",
        description="Agregación simple sobre tabla primaria en periodo relativo (sin group by).",
    ),
]


def choose_template(plan: Dict[str, Any], spec: LinkedSpec) -> Template:
    for t in _TEMPLATES:
        if t.matches(plan, spec):
            return t
    raise ValueError("No hay plantilla compatible con el plan actual.")
