import json
from typing import Dict, Any, List, Tuple

def build_catalog_index(catalog_json_str: str) -> Dict[str, Any]:
    catalog = json.loads(catalog_json_str)
    tables = catalog.get("tables_catalog", [])

    index = {
        "tables": {},          # "cartera.desembolso" -> {schema,name,fields:set}
        "by_name": {},         # "desembolso" -> "cartera.desembolso"
        "fields": {},          # "cartera.desembolso" -> set(fields)
        "time_fields": {},     # "cartera.desembolso" -> list(time fields)
        "join_keys": {},       # "cartera.desembolso" -> join_keys list
        "grain": {},           # "cartera.desembolso" -> grain
    }

    for t in tables:
        schema = t.get("schema")
        name = t.get("name")
        full = f"{schema}.{name}"
        fields = set([f["field"] for f in t.get("field", [])])

        index["tables"][full] = t
        index["by_name"][name] = full
        index["fields"][full] = fields
        index["time_fields"][full] = t.get("time_fields", [])
        index["join_keys"][full] = t.get("join_keys", [])
        index["grain"][full] = t.get("grain", "")

    return index

def qualify_table(index: Dict[str, Any], table_name: str) -> str:
    # acepta "desembolso" o "cartera.desembolso"
    if "." in table_name:
        return table_name
    return index["by_name"].get(table_name, table_name)

def field_exists(index: Dict[str, Any], full_table: str, field: str) -> bool:
    return field in index["fields"].get(full_table, set())
