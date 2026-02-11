from typing import Tuple

def yyyymm_to_date_expr(yyyymm_field: str) -> str:
    # yyyymm_field ya viene como "cartera.desembolso.nCosecha" o alias.nCosecha
    return f"DATEFROMPARTS({yyyymm_field} / 100, {yyyymm_field} % 100, 1)"

def ultimo_mes_declaracion(yyyymm_field: str, from_table: str) -> str:
    # yyyymm_field: "nCosecha" o "nStock" (sin calificar)
    return f"DECLARE @UltimoMes INT = (SELECT MAX({yyyymm_field}) FROM {from_table});"

def ultimos_n_meses_where(yyyymm_field: str, from_table: str, n: int) -> Tuple[str, str]:
    # retorna (declare_sql, where_sql_fragment)
    declare = (
        "DECLARE @FechaMax DATE; "
        f"SELECT @FechaMax = MAX({yyyymm_to_date_expr(yyyymm_field)}) FROM {from_table};"
    )
    where = f"{yyyymm_to_date_expr(yyyymm_field)} >= DATEADD(MONTH, -{n-1}, @FechaMax)"
    return declare, where
