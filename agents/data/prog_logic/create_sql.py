from typing import TypedDict, List, Literal, Dict, Any, Optional, Tuple
from agents.data.prog_logic.catalog import Catalog
from agents.data.prog_logic.normalize import normalize_plan
from agents.data.prog_logic.linker import link_plan
from agents.data.prog_logic.router import choose_template


def create_sql(payload: Dict[str, Any], catalog: Catalog) -> Tuple[str, Dict[str, Any]]:

    plan_norm = normalize_plan(payload)
    spec = link_plan(plan_norm, catalog)
    template = choose_template(plan_norm, spec)
    print("\n")
    print(plan_norm)
    print(template)
    print(spec)
    sql = template.render(plan_norm, spec)
    print(
        """\nRESULTADO LOGICA PROGRAMADA\n============================================================\n"""
    )
    print(sql)

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
