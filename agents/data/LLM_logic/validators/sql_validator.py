# agents/data/LLM_logic/validators/sql_validator.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
import re


# ============================================================
# 1) Construcción de índice de catálogo (robusto)
# ============================================================

def build_catalog_index(catalog: Any) -> Dict[str, Set[str]]:
    idx: Dict[str, Set[str]] = {}
    if catalog is None:
        return idx

    if isinstance(catalog, dict):
        if "tables" in catalog and isinstance(catalog["tables"], list):
            for t in catalog["tables"]:
                schema = (t.get("schema") or "").strip()
                name = (t.get("name") or t.get("table") or "").strip()
                fq = f"{schema}.{name}" if schema else name
                cols: Set[str] = set()
                for c in (t.get("columns") or t.get("fields") or []):
                    if isinstance(c, dict):
                        n = c.get("name") or c.get("field")
                        if n:
                            cols.add(str(n))
                    elif isinstance(c, str):
                        cols.add(c)
                if fq and cols:
                    idx[fq] = cols
            return idx

        for k, v in catalog.items():
            if isinstance(v, dict) and ("columns" in v or "fields" in v):
                cols: Set[str] = set()
                for c in (v.get("columns") or v.get("fields") or []):
                    if isinstance(c, dict):
                        n = c.get("name") or c.get("field")
                        if n:
                            cols.add(str(n))
                    elif isinstance(c, str):
                        cols.add(c)
                if cols:
                    idx[str(k)] = cols
        if idx:
            return idx

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
                        elif isinstance(c, dict):
                            n = c.get("name") or c.get("field")
                            if n:
                                cols.add(str(n))
                        else:
                            n = getattr(c, "name", None)
                            if n:
                                cols.add(str(n))

                cols_dict = getattr(t, "cols", None)
                if isinstance(cols_dict, dict):
                    cols |= set(map(str, cols_dict.keys()))

                if fq and cols:
                    idx[fq] = cols

    return idx


def resolve_table_key(base_table: str, catalog_idx: Dict[str, Set[str]]) -> Optional[str]:
    if not base_table or not catalog_idx:
        return None
    if base_table in catalog_idx:
        return base_table
    bt = base_table.lower()
    candidates = [k for k in catalog_idx.keys() if k.lower().endswith("." + bt)]
    if len(candidates) == 1:
        return candidates[0]
    return None


# ============================================================
# 2) Parsing SQL ligero
# ============================================================

_SQL_KEYWORDS = {
    "select", "from", "where", "group", "by", "order", "having",
    "top", "distinct", "as",
    "join", "inner", "left", "right", "full", "outer", "cross", "on",
    "and", "or", "in", "is", "null", "like", "between", "exists",
    "with", "declare", "set",
    "case", "when", "then", "else", "end",
    "asc", "desc",
}

_SQL_FUNCS = {
    "sum", "avg", "count", "min", "max",
    "round", "cast", "convert", "nullif",
    "coalesce", "isnull",
    "dateadd", "datediff", "datefromparts", "getdate",
}

_IGNORE_TOKENS = _SQL_KEYWORDS | _SQL_FUNCS


def _strip_strings(sql: str) -> str:
    return re.sub(r"'([^']|'')*'", "''", sql)


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql


def _one_line(sql: str) -> str:
    return " ".join((sql or "").replace("\n", " ").replace("\r", " ").split())


def _extract_clause(sql: str, start_kw: str, end_kws: List[str]) -> str:
    s = _one_line(_strip_strings(_strip_comments(sql))).lower()
    m = re.search(rf"\b{re.escape(start_kw)}\b", s)
    if not m:
        return ""
    start = m.end()
    tail = s[start:]
    end = len(tail)
    for ek in end_kws:
        mm = re.search(rf"\b{re.escape(ek)}\b", tail)
        if mm:
            end = min(end, mm.start())
    return tail[:end].strip()


def extract_select_sql(sql: str) -> str:
    return _extract_clause(sql, "select", ["from"])


def extract_where_sql(sql: str) -> str:
    return _extract_clause(sql, "where", ["group by", "order by", "having"])


def extract_group_by_sql(sql: str) -> str:
    s = _one_line(_strip_strings(_strip_comments(sql))).lower()
    m = re.search(r"\bgroup\s+by\b", s)
    if not m:
        return ""
    tail = s[m.end():]
    end = len(tail)
    for ek in ["order by", "having"]:
        mm = re.search(rf"\b{re.escape(ek)}\b", tail)
        if mm:
            end = min(end, mm.start())
    return tail[:end].strip()


def _split_csv(expr: str) -> List[str]:
    items = []
    buf = []
    depth = 0
    for ch in expr:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            item = "".join(buf).strip()
            if item:
                items.append(item)
            buf = []
        else:
            buf.append(ch)
    last = "".join(buf).strip()
    if last:
        items.append(last)
    return items


def _is_aggregated(expr: str) -> bool:
    e = expr.lower()
    return any(fn in e for fn in ("sum(", "avg(", "count(", "min(", "max("))


def _extract_identifiers(expr: str) -> Set[str]:
    e = _strip_strings(_strip_comments(expr))
    tokens = re.findall(r"\b[a-z_][\w\.]*\b", e, flags=re.I)

    out: Set[str] = set()
    for t in tokens:
        tl = t.lower()
        if tl in _IGNORE_TOKENS:
            continue
        col = t.split(".")[-1]
        if col.lower() in _IGNORE_TOKENS:
            continue
        if "." not in t and len(col) <= 2:
            continue
        out.add(col)
    return out


# ============================================================
# 3) Validaciones generales (NO sobreajustadas)
# ============================================================

def validate_columns_exist(sql: str, allowed_cols: Set[str]) -> List[str]:
    issues: List[str] = []
    if not allowed_cols:
        return issues

    select_sql = extract_select_sql(sql)
    where_sql = extract_where_sql(sql)
    group_sql = extract_group_by_sql(sql)

    referenced: Set[str] = set()
    for part in (select_sql, where_sql, group_sql):
        if part:
            referenced |= _extract_identifiers(part)

    missing = sorted([c for c in referenced if c not in allowed_cols])
    if missing:
        issues.append(f"Columnas no encontradas en catálogo: {missing}")
    return issues


def validate_group_by(sql: str) -> List[str]:
    issues: List[str] = []
    select_sql = extract_select_sql(sql)
    group_sql = extract_group_by_sql(sql)

    if not select_sql or not group_sql:
        return issues

    select_items = _split_csv(select_sql)
    group_items_raw = [x.strip() for x in group_sql.split(",") if x.strip()]
    group_cols = set([g.split(".")[-1].strip().lower() for g in group_items_raw])

    required: List[str] = []
    for it in select_items:
        it_clean = it.strip()
        if not it_clean:
            continue
        if _is_aggregated(it_clean):
            continue
        if re.fullmatch(r"\d+(\.\d+)?", it_clean):
            continue

        ids = _extract_identifiers(it_clean)
        if len(ids) == 1:
            required.append(next(iter(ids)))
        else:
            required.append(it_clean)

    missing: List[str] = []
    for r in required:
        rl = r.lower()
        if re.fullmatch(r"[a-z_]\w*", r, flags=re.I):
            if rl not in group_cols:
                missing.append(r)
        else:
            if rl not in [g.lower() for g in group_items_raw]:
                missing.append(r)

    if missing:
        issues.append(f"GROUP BY no incluye todas las dimensiones no agregadas del SELECT: {missing}")
    return issues


def validate_no_group_by_for_scalar(sql: str, result_shape: Optional[str]) -> List[str]:
    """
    Regla general:
    - Si el planner decidió scalar => NO debe haber GROUP BY.
    """
    issues: List[str] = []
    if (result_shape or "").lower() == "scalar":
        if extract_group_by_sql(sql):
            issues.append("result_shape=scalar => NO uses GROUP BY (debe devolver un único escalar).")
    return issues


def validate_bad_nullif_usage(sql: str) -> List[str]:
    """
    Detecta NULLIF mal formado: NULLIF(expr) o NULLIF(expr,) etc.
    Regla general: NULLIF(expr, 0) (2 args).
    """
    issues: List[str] = []
    select_sql = extract_select_sql(sql)
    if not select_sql:
        return issues

    s = _one_line(select_sql)

    # Captura NULLIF( ... ) de manera tolerante
    for m in re.finditer(r"\bnullif\s*\(", s, flags=re.I):
        # extraer el contenido entre paréntesis balanceados
        start = m.end()
        depth = 1
        i = start
        while i < len(s) and depth > 0:
            if s[i] == "(":
                depth += 1
            elif s[i] == ")":
                depth -= 1
            i += 1
        inside = s[start:i-1].strip() if i > start else ""

        # ahora validamos si tiene coma y segundo argumento 0 (aprox)
        if "," not in inside:
            issues.append("NULLIF mal formado: NULLIF requiere 2 argumentos (NULLIF(expr, 0)).")
            break

        # chequeo suave: que termine con 0 o 0.0 como segundo argumento (no obligado, pero deseable)
        # no bloqueamos si no es exactamente 0, pero sí si está vacío
        parts = [p.strip() for p in inside.split(",", 1)]
        if len(parts) < 2 or not parts[1]:
            issues.append("NULLIF mal formado: segundo argumento vacío (debe ser 0).")
            break

    return issues


def validate_ratio_nullif_denominator(sql: str) -> List[str]:
    """
    Regla general:
    - Si hay '/', el denominador debe estar protegido con NULLIF(den,0).
    Heurística: busca '/' en SELECT y exige NULLIF(...) a la derecha inmediata.
    """
    issues: List[str] = []
    select_sql = extract_select_sql(sql)
    if not select_sql or "/" not in select_sql:
        return issues

    s = _one_line(select_sql)

    for m in re.finditer(r"/", s):
        right = s[m.end(): m.end() + 160]
        if "nullif(" not in right.lower():
            issues.append("Ratio/porcentaje detectado: protege el DENOMINADOR con NULLIF(denominador, 0).")
            break

    return issues


def validate_no_nullif_in_numerator_for_ratio(sql: str) -> List[str]:
    """
    Regla general:
    - En ratios, NULLIF debe usarse SOLO en el denominador.
    Heurística: si hay '/', revisa ventana a la izquierda y si aparece 'NULLIF(' => issue.
    """
    issues: List[str] = []
    select_sql = extract_select_sql(sql)
    if not select_sql or "/" not in select_sql:
        return issues

    s = _one_line(select_sql)

    for m in re.finditer(r"/", s):
        left = s[max(0, m.start() - 180): m.start()]
        if "nullif(" in left.lower():
            issues.append("Uso inválido: en ratios/porcentajes NO uses NULLIF en el numerador. Solo en el denominador.")
            break

    return issues


def validate_sql_reasoning(sql: str, allowed_cols: Set[str], result_shape: Optional[str] = None) -> Dict[str, Any]:
    """
    Motor de validación general:
    - columnas en catálogo
    - GROUP BY consistente
    - scalar => sin GROUP BY
    - NULLIF bien formado
    - ratio => NULLIF en denominador, NO en numerador
    """
    issues: List[str] = []
    issues.extend(validate_bad_nullif_usage(sql))
    issues.extend(validate_no_group_by_for_scalar(sql, result_shape))
    issues.extend(validate_columns_exist(sql, allowed_cols))
    issues.extend(validate_group_by(sql))
    issues.extend(validate_ratio_nullif_denominator(sql))
    issues.extend(validate_no_nullif_in_numerator_for_ratio(sql))

    if issues:
        return {"ok": False, "issues": issues, "error": " | ".join(issues)}
    return {"ok": True, "issues": []}


def build_fix_prompt(
    original_sql: str,
    issues: List[str],
    plan_view: Dict[str, Any],
    allowed_columns: List[str],
) -> str:
    return f"""
Eres un experto en SQL Server.

Corrige el SQL para que sea ejecutable y consistente.

REGLAS DURAS:
- Devuelve SOLO SQL (sin markdown, sin explicación, sin comentarios).
- Respeta EXACTAMENTE FROM/JOIN/WHERE del plan. NO los cambies.
- NO inventes columnas: usa SOLO columnas de ALLOWED_COLUMNS.
- Si result_shape=scalar => NO uses GROUP BY.
- GROUP BY: toda columna NO agregada del SELECT debe estar en GROUP BY.
- Ratios/porcentajes: NULLIF SOLO en el DENOMINADOR (NULLIF(den, 0)). NO uses NULLIF en el numerador.
- NULLIF siempre debe tener 2 argumentos: NULLIF(expr, 0).
- No metas texto fuera del SQL.

ALLOWED_COLUMNS:
{allowed_columns}

PLAN:
{plan_view}

ERRORES:
- """ + "\n- ".join(issues) + f"""

SQL ACTUAL:
{original_sql}

Devuelve el SQL corregido completo.
""".strip()
