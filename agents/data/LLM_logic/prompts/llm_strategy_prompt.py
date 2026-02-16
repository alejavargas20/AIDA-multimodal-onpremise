# agents/data/LLM_logic/prompts/llm_strategy_prompt.py
from __future__ import annotations

from typing import Any, Dict, List, Set, Optional
import json
import re


# ---------------------------
# Catálogo -> columnas de tabla base
# ---------------------------

def _build_catalog_index(catalog: Any) -> Dict[str, Set[str]]:
    """
    Construye índice { "cartera.desembolso": {"nMonto","cRegion",...}, ... }
    Soporta:
    - Catalog object con .tables
    - dict con {"tables":[{schema,name,columns:[...]}]}
    - dict con {"cartera.desembolso":{"columns":[...]}}
    """
    idx: Dict[str, Set[str]] = {}
    if catalog is None:
        return idx

    # dict estilo {"tables":[...]}
    if isinstance(catalog, dict) and isinstance(catalog.get("tables"), list):
        for t in catalog["tables"]:
            schema = (t.get("schema") or "").strip()
            name = (t.get("name") or t.get("table") or "").strip()
            fq = f"{schema}.{name}" if schema else name
            cols: Set[str] = set()
            for c in (t.get("columns") or []):
                if isinstance(c, dict) and c.get("name"):
                    cols.add(c["name"])
                elif isinstance(c, str):
                    cols.add(c)
            if fq and cols:
                idx[fq] = cols
        return idx

    # dict estilo {"cartera.desembolso":{"columns":[...]}}
    if isinstance(catalog, dict):
        for k, v in catalog.items():
            if isinstance(v, dict) and "columns" in v:
                cols: Set[str] = set()
                for c in (v.get("columns") or []):
                    if isinstance(c, dict) and c.get("name"):
                        cols.add(c["name"])
                    elif isinstance(c, str):
                        cols.add(c)
                if cols:
                    idx[str(k)] = cols
        if idx:
            return idx

    # Catalog object con .tables
    if hasattr(catalog, "tables"):
        tables = getattr(catalog, "tables")
        if isinstance(tables, dict):
            for k, t in tables.items():
                fq = str(getattr(t, "full_name", "") or getattr(t, "name", "") or k)
                schema = getattr(t, "schema", None)
                if schema and "." not in fq:
                    fq = f"{schema}.{fq}"

                cols: Set[str] = set()
                cols_src = getattr(t, "columns", None)
                if isinstance(cols_src, list):
                    for c in cols_src:
                        if isinstance(c, str):
                            cols.add(c)
                        elif isinstance(c, dict) and c.get("name"):
                            cols.add(c["name"])
                        else:
                            n = getattr(c, "name", None)
                            if n:
                                cols.add(str(n))
                if fq and cols:
                    idx[fq] = cols

    return idx


def _resolve_base_table_columns(catalog: Any, base_table: str) -> List[str]:
    idx = _build_catalog_index(catalog)
    if not idx or not base_table:
        return []

    # match directo
    if base_table in idx:
        return sorted(idx[base_table])

    # match por sufijo si viniera sin esquema
    candidates = [k for k in idx.keys() if k.lower().endswith("." + base_table.lower())]
    if len(candidates) == 1:
        return sorted(idx[candidates[0]])

    return []


# ---------------------------
# Heurística mínima de mapping (no destructiva)
# ---------------------------

_FIELD_SYNONYMS = {
    # desembolso
    "monto": ["nMonto"],
    "monto_desembolsado": ["nMonto"],
    "plazo": ["nPlazo"],
    "producto": ["cProducto"],
    "region": ["cRegion"],
    "oficina": ["cOficina"],
    "cliente_nuevo": ["nClienteNue"],
    # cierre
    "mora": ["nMora"],
    "saldo": ["nSaldoCap", "nSaldo"],
    "saldo_capital": ["nSaldoCap"],
    # comunes
    "idcliente": ["idCliente"],
    "idcuenta": ["idCuenta"],
    "ncosecha": ["nCosecha"],
    "nstock": ["nStock"],
}


def _map_field_to_catalog(field_norm: str, available_cols: List[str]) -> Optional[str]:
    """
    Intenta mapear un field_norm ("region") a una columna real ("cRegion"),
    usando sinónimos y chequeo contra columnas disponibles.
    """
    if not field_norm or not available_cols:
        return None

    cols_set = set(available_cols)

    # match directo
    for c in available_cols:
        if c.lower() == field_norm.lower():
            return c

    # sinónimos
    for cand in _FIELD_SYNONYMS.get(field_norm.lower(), []):
        if cand in cols_set:
            return cand

    # heurística: contiene el token (ej "region" -> "cRegion")
    token = field_norm.lower()
    candidates = [c for c in available_cols if token in c.lower()]
    if len(candidates) == 1:
        return candidates[0]

    return None


def _normalize_filters_for_prompt(filters: List[Dict[str, Any]], available_cols: List[str]) -> List[Dict[str, Any]]:
    """
    Produce filtros con:
      - field_norm
      - mapped_column (si se puede)
      - operator ajustado (texto con '=' -> LIKE)
    """
    out: List[Dict[str, Any]] = []
    for f in (filters or []):
        if not isinstance(f, dict):
            continue
        field = str(f.get("field") or "")
        field_norm = (f.get("field_norm") or field).strip().lower()
        op = str(f.get("operator") or "").strip()
        val = f.get("value")

        mapped = _map_field_to_catalog(field_norm, available_cols)

        # regla: "=" con texto descriptivo => LIKE
        op2 = op
        val2 = val
        if op == "=" and isinstance(val, str):
            v = val.strip()
            # si parece texto (no numérico/código corto), usar LIKE
            if not re.fullmatch(r"\d+(\.\d+)?", v) and len(v) >= 3:
                op2 = "LIKE"
                val2 = f"%{v}%"

        out.append({
            "field": field,
            "field_norm": field_norm,
            "mapped_column": mapped,
            "operator": op2,
            "value": val2,
            "table": f.get("table"),
        })
    return out


# ---------------------------
# Prompt “arquitecto SQL”
# ---------------------------

def build_llm_strategy_prompt(
    *,
    question: str,
    plan_view: Dict[str, Any],
    input_data: Dict[str, Any],
    catalog: Any
) -> str:
    """
    Prompt de estrategia:
    - columnas reales permitidas (tabla base)
    - filtros estructurados + mapping sugerido
    - reglas de decisión (scalar vs grouped vs series)
    - reglas para ratio/percent
    """
    base_table = plan_view.get("base_table") or ""
    available_cols = _resolve_base_table_columns(catalog, base_table)

    metric = (input_data.get("metric") or {})
    agg = (metric.get("aggregation") or {})
    agg_type = (agg.get("type") or agg.get("key") or "").strip().lower()

    filters = input_data.get("filters") or []
    filters_norm = _normalize_filters_for_prompt(filters, available_cols)

    # dimensiones (si existen)
    dims = input_data.get("dimensions") or []
    dims_mapped = []
    for d in dims:
        if isinstance(d, str):
            mapped = _map_field_to_catalog(d.strip().lower(), available_cols)
            dims_mapped.append({"dimension": d, "mapped_column": mapped})
        elif isinstance(d, dict):
            dn = (d.get("field_norm") or d.get("field") or "").strip().lower()
            mapped = _map_field_to_catalog(dn, available_cols)
            dims_mapped.append({"dimension": d, "mapped_column": mapped})

    cols_block = ", ".join(available_cols[:200]) if available_cols else "(catálogo no disponible en runtime)"
    if available_cols and len(available_cols) > 200:
        cols_block += " ..."

    return f"""
Eres un arquitecto SQL (SQL Server) especializado en analítica crediticia.
Tu trabajo es generar SQL correcto, simple, y consistente con el plan.

REGLAS NO NEGOCIABLES:
1) Devuelve SOLO SQL. Sin markdown, sin explicación, sin comentarios.
2) NO inventes tablas/alias tipo dbo.Tabla. Usa SOLO columnas reales del catálogo.
3) No cambies FROM/JOIN/WHERE del plan (eso lo controla el planner).
4) Si es ratio/porcentaje: el denominador debe usar NULLIF(...,0).
5) NO uses GROUP BY si el resultado esperado es escalar.
   - Ejemplo: "¿qué porcentaje ... en la región Sur?" => escalar.
   - Solo agrupas si la pregunta explícitamente pide "por región", "por producto", etc.
6) Si llega un filtro texto con operador "=" (p.ej. Sur, Campaña, PYME):
   - conviértelo a LIKE '%valor%'.

PREGUNTA:
{question}

PLAN (no modificar FROM/JOIN/WHERE):
{json.dumps(plan_view, ensure_ascii=False, indent=2)}

SEÑALES ESTRUCTURALES (intent input):
- agg_type: {agg_type}
- filters (con mapping sugerido):
{json.dumps(filters_norm, ensure_ascii=False, indent=2)}
- dimensions (si aplica):
{json.dumps(dims_mapped, ensure_ascii=False, indent=2)}

CATÁLOGO (columnas permitidas en {base_table}):
{cols_block}

OBJETIVO:
- Escribe el SELECT final (y si aplica GROUP BY/ORDER BY) para responder la pregunta.
- Usa las columnas mapeadas cuando existan (mapped_column).
""".strip()
