def expr_today_date() -> str:
    return "CAST(GETDATE() AS date)"


def expr_period_start_relative(period_key: str) -> str:
    """
    Devuelve una expresión SQL Server que representa el inicio del periodo relativo.
    Ej: last_month -> DATEADD(month, -1, CAST(GETDATE() AS date))
    """
    k = (period_key or "").lower()

    if k == "ultimo_mes":
        return "DATEADD(month, -1, CAST(GETDATE() AS date))"
    if (k == "ultimo_trimestre") or (k == "ultimos_3_meses"):
        return "DATEADD(month, -3, CAST(GETDATE() AS date))"
    if k == "ultimo_año":
        return "DATEADD(year, -1, CAST(GETDATE() AS date))"
    if (k == "ultima_semana") or (k == "ultimos_7_dias"):
        return "DATEADD(day, -7, CAST(GETDATE() AS date))"
    if k == "ultimos_30_dias":
        return "DATEADD(day, -30, CAST(GETDATE() AS date))"
    if k == "ultimo_6_meses":
        return "DATEADD(month, -6, CAST(GETDATE() AS date))"

    raise ValueError(f"Periodo relativo no soportado: {period_key}")
