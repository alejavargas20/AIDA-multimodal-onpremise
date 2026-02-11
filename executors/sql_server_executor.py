import pyodbc
from typing import Any, Dict, List, Optional

def execute_sql(sql: str,
                server: str = r"JORDAN\SQLEXPRESS",
                database: str = "BD_GINF",
                trusted_connection: bool = True,
                username: str = None,
                password: str = None,
                mode: str = "scalar",
                max_rows: int = 200) -> Dict[str, Any]:
    """
    mode:
      - scalar: devuelve fetchone()[0]
      - table: devuelve columnas + filas (hasta max_rows)
    """
    try:
        if trusted_connection:
            conn_str = (
                f"DRIVER={{SQL Server}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                "Trusted_Connection=yes;"
            )
        else:
            if not username or not password:
                raise ValueError("Se requiere username y password para autenticación SQL")
            conn_str = (
                f"DRIVER={{SQL Server}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"UID={username};"
                f"PWD={password};"
            )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(sql)

        if mode == "table":
            columns = [c[0] for c in cursor.description] if cursor.description else []
            rows = cursor.fetchmany(max_rows)
            data = [list(r) for r in rows]
            cursor.close()
            conn.close()
            return {"status": "success", "columns": columns, "rows": data, "sql_executed": sql.strip()}

        row = cursor.fetchone()
        result_value = row[0] if row else None

        cursor.close()
        conn.close()

        return {"status": "success", "result": result_value, "sql_executed": sql.strip()}

    except pyodbc.Error as e:
        return {"status": "error", "error": str(e), "sql": sql.strip()}
    except Exception as e:
        return {"status": "error", "error": f"Error inesperado: {str(e)}", "sql": sql.strip()}
