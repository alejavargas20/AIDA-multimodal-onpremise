from typing import TypedDict, List, Literal, Dict, Any, Optional
from agents.data.prog_logic.catalog import Catalog
from agents.data.prog_logic.create_sql import create_sql
from agents.data.executors.sql_server_executor import execute_sql
from agents.data.LLM_logic.main_LLM import create_sql_LLM
from agents.data.LLM_logic.utils import _extract_id_cliente


def process(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload esperado (del orquestador):
      - normalized_text (str)
      - optimized_prompt (str)
      - intent_json (dict) opcional
    """

    print("Ha entrado bien en el agente de data")
    CATALOG_PATH = "agents/data/catalog.json"
    catalog = Catalog.from_json(CATALOG_PATH)
    print("Catalogo creado correctamente")

    # IdCliente (si aplica)
    print("Extracción de clientes")
    params = payload.get("metadata", {}) or {}
    id_cliente = _extract_id_cliente(params)

    try:
        print("Entra por Logica programada")
        # Logica Programada
        sql = create_sql(payload, catalog, id_cliente)
    except Exception as e:
        print(type(e).__name__, ":", e)
        # LLM
        print("\nEntra por LLM")
        sql, mode = create_sql_LLM(payload, catalog, id_cliente)

    print(sql)

    execution_result = execute_sql(sql, mode=mode)

    return {
        "status": "success",
        "sql": sql,
        "execution_result": execution_result,
    }
