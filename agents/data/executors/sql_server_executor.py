# # aida-multimodal-onpremise/agents/data/executors/sql_server_executor.py
# import pyodbc
# from typing import Any, Dict, List, Optional


# def execute_sql(
#     sql: str,
#     server: str = r"JORDAN\SQLEXPRESS",
#     database: str = "BD_GINF",
#     trusted_connection: bool = True,
#     username: str = None,
#     password: str = None,
#     mode: str = "scalar",
#     max_rows: int = 200,
# ) -> Dict[str, Any]:
#     """
#     mode:
#       - scalar: devuelve fetchone()[0]
#       - table: devuelve columnas + filas (hasta max_rows)
#     """
#     try:
#         if trusted_connection:
#             conn_str = (
#                 f"DRIVER={{SQL Server}};"
#                 f"SERVER={server};"
#                 f"DATABASE={database};"
#                 "Trusted_Connection=yes;"
#             )
#         else:
#             if not username or not password:
#                 raise ValueError(
#                     "Se requiere username y password para autenticación SQL"
#                 )
#             conn_str = (
#                 f"DRIVER={{SQL Server}};"
#                 f"SERVER={server};"
#                 f"DATABASE={database};"
#                 f"UID={username};"
#                 f"PWD={password};"
#             )

#         conn = pyodbc.connect(conn_str)
#         cursor = conn.cursor()
#         cursor.execute(sql)

#         if mode == "table":
#             columns = [c[0] for c in cursor.description] if cursor.description else []
#             rows = cursor.fetchmany(max_rows)
#             data = [list(r) for r in rows]
#             cursor.close()
#             conn.close()
#             return {
#                 "status": "success",
#                 "columns": columns,
#                 "rows": data,
#                 "sql_executed": sql.strip(),
#             }

#         row = cursor.fetchone()
#         result_value = row[0] if row else None

#         cursor.close()
#         conn.close()

#         return {
#             "status": "success",
#             "result": result_value,
#             "sql_executed": sql.strip(),
#         }

#     except pyodbc.Error as e:
#         return {"status": "error", "error": str(e), "sql": sql.strip()}
#     except Exception as e:
#         return {
#             "status": "error",
#             "error": f"Error inesperado: {str(e)}",
#             "sql": sql.strip(),
#         }


import pandas as pd
import sys
import os
from typing import Any, Dict, List, Optional  
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pandas')

# Rutas para encontrar backend
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
if root_dir not in sys.path:
    sys.path.append(root_dir)
try:
    from backend.db.connection import get_db
except ImportError:
    sys.path.append(os.path.join(os.getcwd()))
    from backend.db.connection import get_db

def execute_sql(
    sql: str,
    server: str = None,   
    database: str = None, 
    trusted_connection: bool = True, 
    username: str = None, 
    password: str = None, 
    mode: str = "scalar", 
    max_rows: int = 200, 
    **kwargs            
) -> Dict[str, Any]:
    """
    Ejecuta SQL usando la conexión centralizada (get_db).
    Ignora los parámetros de conexión hardcodeados para priorizar la seguridad del entorno.
    """
    conn = None
    try:
        conn = get_db()
        
        # Limpiamos el SQL de posibles inyecciones markdown del LLM por si acaso
        clean_sql = sql.replace("```sql", "").replace("```", "").strip()
        
        # Ejecutamos con Pandas
        df = pd.read_sql(clean_sql, conn)
        
        # Control de Dataframe vacío
        if df.empty:
            return {
                "status": "success",
                "result": None if mode == 'scalar' else [],
                "sql_executed": clean_sql
            }

        # Lógica Escalar
        if mode == 'scalar':
            val = df.iloc[0, 0]
            if hasattr(val, 'item'): 
                val = val.item()
            
            return {
                "status": "success",
                "result": val,
                "sql_executed": clean_sql
            }
            
        df_limited = df.head(max_rows)
        # Convertimos fechas y nulos para que el JSON no explote en el Frontend
        df_clean = df_limited.fillna("").astype(str)

        return {
            "status": "success",
            "columns": list(df_clean.columns),
            "rows": df_clean.to_dict(orient='records'),
            "sql_executed": clean_sql
        }

    except Exception as e:
        return {"status": "error", "error": str(e), "sql": sql}
    
    finally:
        if conn:
            conn.close()
