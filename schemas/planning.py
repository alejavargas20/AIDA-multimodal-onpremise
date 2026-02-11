from typing import TypedDict, List, Dict, Optional, Literal

ResultShape = Literal["scalar", "grouped", "series", "detail"]

class TimePlan(TypedDict, total=False):
    mode: Literal["ultimo_mes", "ultimos_n_meses", "rango_yyyymm"]
    field: str                 # nCosecha / nStock (ya calificado con esquema)
    n_months: int              # para ultimos_n_meses
    start_yyyymm: int
    end_yyyymm: int

class JoinPlan(TypedDict, total=False):
    recipe: Literal["none", "desembolso__cierre", "desembolso__cosecha_sal", "cliente__cuentas_activas", "cuentas_activas__comportamiento"]
    joins_sql: str

class QueryPlan(TypedDict, total=False):
    base_table: str            # ej: "cartera.desembolso"
    result_shape: ResultShape
    preamble_sql: str
    from_sql: str              # FROM + JOINs listos
    where_sql: str             # WHERE listo (sin el SELECT)
    group_by_fields: List[str] # ya calificados
    allowed_tables: List[str]
    allowed_fields: Dict[str, List[str]]
    notes: str
