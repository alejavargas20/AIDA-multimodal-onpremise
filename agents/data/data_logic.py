# aida-multimodal-onpremise/agents/data/data_logic.py
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

    sql = ""
    mode = "table"

    try:
        print("Entra por Logica programada")
        # Logica Programada
        # sql = create_sql(payload, catalog, id_cliente)
        resultado = create_sql(payload, catalog, id_cliente)

        # Si la lógica programada devuelve una tupla (sql, mode), los asignamos
        if isinstance(resultado, tuple) and len(resultado) == 2:
            sql, mode = resultado
        else:
            # Si solo devuelve el string del SQL, forzamos mode='table'
            sql = str(resultado)
            mode = "table"

    except Exception as e:
        print(type(e).__name__, ":", e)
        # LLM
        print("\nEntra por LLM")
        sql, mode = create_sql_LLM(payload, catalog, id_cliente)

    print(f"\n[SQL GENERADO]:\n{sql}\n")

    # Si por alguna razón sql sigue vacío, devolvemos error antes de golpear la BBDD
    if not sql:
        return {"status": "error", "error": "No se pudo generar SQL."}

    execution_result = execute_sql(sql, mode=mode)

    return {
        "status": "success",
        "sql": sql,
        "execution_result": execution_result,
    }
