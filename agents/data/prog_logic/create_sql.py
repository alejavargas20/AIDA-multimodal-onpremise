from typing import TypedDict, List, Literal, Dict, Any, Optional, Tuple
from agents.data.prog_logic.catalog import Catalog
from agents.data.prog_logic.normalize import normalize_plan
from agents.data.prog_logic.linker import link_plan
from agents.data.prog_logic.router import choose_template


def create_sql(
    payload: Dict[str, Any], catalog: Catalog, id_cliente=str
) -> Tuple[str, Dict[str, Any]]:

    plan_norm = normalize_plan(payload)
    spec = link_plan(plan_norm, catalog)
    template = choose_template(plan_norm, spec)
    print("\n")
    sql = template.render(plan_norm, spec)

    if id_cliente is not None:
        sql = sql.replace(
            "WHERE", f"WHERE {spec.table}.idCliente = '{id_cliente}' AND", 1
        )

    print(
        """\nRESULTADO LOGICA PROGRAMADA\n============================================================\n"""
    )

    # meta = {
    #     "template": template.name,
    #     "table": spec.table,
    #     "aggregation_key": spec.agg_key,
    #     "metric_column": spec.metric_column,
    #     "metric_type": spec.metric_type,
    #     "date_column": spec.date_column,
    #     "where_clauses": spec.where_clauses,
    # }
    return sql
