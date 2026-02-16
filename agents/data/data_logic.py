from typing import Dict, Any
from agents.data.prog_logic.catalog import Catalog
from agents.data.prog_logic.create_sql import create_sql
from agents.data.executors.sql_server_executor import execute_sql
from agents.data.LLM_logic.main_LLM import create_sql_LLM
from agents.data.LLM_logic.utils import _extract_id_cliente

def _is_empty(result: Any) -> bool:
    try:
        if result is None:
            return True
        # Si execute_sql devolvió dict
        if isinstance(result, dict):
            # si hubo error, lo tratamos como vacío/error
            if result.get("status") == "error":
                return True
            # ✅ caso escalar: viene en "result"
            if "result" in result:
                return result["result"] is None
            # caso tabla: viene en "rows"
            if "rows" in result and isinstance(result["rows"], list):
                return len(result["rows"]) == 0
            # si no reconocemos el formato, lo tratamos como vacío
            return True

        # si fuera un escalar directo (por si cambias executor a futuro)
        if isinstance(result, (int, float, str, bool)):
            return False
        if isinstance(result, list):
            return len(result) == 0
        if hasattr(result, "empty"):
            return result.empty
        return True
    except:
        return True

def _guess_mode(sql: str, default: str = "scalar") -> str:
    s = " ".join(sql.lower().split())
    # ✅ si hay group by, casi seguro es tabla
    if " group by " in s:
        return "table"
    # ✅ si el select tiene comas, suele ser más de una columna -> tabla
    if s.startswith("select") and "," in s.split("from", 1)[0]:
        return "table"
    return default

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


    # modo por defecto para que siempre exista
    mode = "scalar"

    # IdCliente (si aplica)
    print("Extracción de clientes")
    params = payload.get("metadata", {}) or {}
    id_cliente = _extract_id_cliente(params)


    try:
        print("Entra por Logica programada")
        # Logica Programada

        sql = create_sql(payload, catalog, id_cliente)
        # ejecuta aquí para poder evaluar si vino vacío
        mode = _guess_mode(sql, default="scalar")
        execution_result = execute_sql(sql, mode=mode)
        print("\n[PROG] SQL: "+sql)

        # si no hay resultados, fallback a LLM + re-ejecución
        if _is_empty(execution_result):
            print("Sin resultados en ejecución con lógica programada. Entra por LLM")
            sql, mode = create_sql_LLM(payload, catalog, id_cliente)
            mode = _guess_mode(sql, default="scalar")
            print("\n[LLM] Voy a ejecutar SQL:")
            execution_result = execute_sql(sql, mode=mode)
            print("\n[LLM] SQL: "+sql)


    except Exception as e:
        print(type(e).__name__, ":", e)
        # LLM
        print("\nEntra por LLM")
        sql, mode = create_sql_LLM(payload, catalog, id_cliente)
        mode = _guess_mode(sql, default="scalar")
        # ejecución cuando entra por LLM 
        execution_result = execute_sql(sql, mode=mode)
        print("\n[LLM] SQL: "+sql)
        
    print(execution_result)


    return {
        "status": "success",
        "sql": sql,
        "execution_result": execution_result,
    }
