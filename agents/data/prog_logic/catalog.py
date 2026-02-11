from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
import json


@dataclass(frozen=True)
class Column:
    name: str
    col_type: str
    sensitive: bool
    description: str = ""


@dataclass
class Table:
    name: str
    fields: Dict[str, Column]  # field_name -> Column
    measures_by_sem: Dict[str, Column]  # semantic -> Column
    times_by_sem: Dict[str, Column]  # semantic -> Column
    rls_field: Optional[str]


class Catalog:
    """Loads your catalog_prompt.json and provides fast lookups."""

    def __init__(self, tables: Dict[str, Table]):
        self.tables = tables

    @classmethod
    def from_json(cls, path: str) -> "Catalog":
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        tables: Dict[str, Table] = {}
        for t in raw.get("tables_catalog", []):
            name = t["name"]

            fields: Dict[str, Column] = {}
            for fdef in t.get("field", []):
                fname = fdef["field"]
                ftype = str(fdef.get("type", "any"))
                sens = str(fdef.get("sensible", "No")).lower() == "yes"
                desc = (
                    str(fdef.get("description", ""))
                    if fdef.get("description") is not None
                    else ""
                )
                fields[fname] = Column(
                    name=fname, col_type=ftype, sensitive=sens, description=desc
                )

            measures_by_sem: Dict[str, Column] = {}
            for m in t.get("measures", []):
                sem = str(m.get("semantic", "")).lower()
                fld = m.get("field")
                if sem and fld in fields:
                    measures_by_sem[sem] = fields[fld]

            times_by_sem: Dict[str, Column] = {}
            for tf in t.get("time_fields", []):
                sem = str(tf.get("semantic", "")).lower()
                fld = tf.get("field")
                if sem and fld in fields:
                    times_by_sem[sem] = fields[fld]

            rls = (t.get("row_level_security") or {}).get("field")
            tables[name] = Table(
                name=name,
                fields=fields,
                measures_by_sem=measures_by_sem,
                times_by_sem=times_by_sem,
                rls_field=rls,
            )

        return cls(tables)

    def table(self, name: str) -> Table:
        if name not in self.tables:
            raise KeyError(f"Tabla no encontrada en catálogo: {name}")
        return self.tables[name]
