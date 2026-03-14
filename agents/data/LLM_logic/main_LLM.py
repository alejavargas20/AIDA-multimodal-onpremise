# agents/data/LLM_logic/main_LLM.py
from __future__ import annotations
from typing import Dict, Any, Tuple, Set, Optional
import re

from agents.data.LLM_logic.utils import is_safe_sql
from agents.data.LLM_logic.planners.intent_planner import plan_query
from agents.data.LLM_logic.prompts.sql_prompt_builder import build_sql_prompt
#from agents.data.LLM_logic.engines.ollama_engine import call_ollama
from agents.data.LLM_logic.normalize_intent import normalize_for_llm
from agents.data.LLM_logic.validators.sql_validator import (
    build_catalog_index,
    resolve_table_key,
    validate_sql_reasoning,
    build_fix_prompt,
)

#MODEL = "mistral:latest"

from agents.local_engine import generate_response

def _clean_llm_output(text: str) -> str:
    if not text:
        return ""
    t = text.strip()

    if "```" in t:
        parts = t.split("```")
        candidate = ""
        for p in parts:
            if "select" in p.lower():
                candidate = p
                break
        t = candidate.strip() if candidate else t.replace("```", "").strip()

    lo = t.lower()
    idx = lo.find("select")
    if idx >= 0:
        t = t[idx:].strip()

    return t


def _allowed_cols_from_catalog(catalog: Any, base_table: str) -> Set[str]:
    catalog_idx = build_catalog_index(catalog)
    key = resolve_table_key(base_table, catalog_idx) or base_table
    return set(catalog_idx.get(key) or set())


def _ends_with_select_query(sql: str) -> bool:
    if not sql:
        return False
    s = sql.strip()
    parts = [p.strip() for p in s.split(";") if p.strip()]
    if not parts:
        return False
    return parts[-1].lower().startswith("select")


def _default_cols_for_base_table(base_table: str) -> Set[str]:
    """
    Defaults razonables SOLO cuando el catálogo no está disponible
    (evita NULL en fallback).
    No sobreajusta: son columnas “típicas” del dominio.
    """
    bt = (base_table or "").lower()
    if bt.endswith("cartera.desembolso") or bt.endswith(".desembolso") or bt == "desembolso":
        return {"nMonto", "cRegion", "cProducto", "cOficina", "nCosecha", "idCliente", "idCuenta"}
    if bt.endswith("cartera.cierre") or bt.endswith(".cierre") or bt == "cierre":
        return {"nStock", "nSaldoCap", "nMora", "idCliente", "idCuenta"}
    return set()


_FIELD_SYNONYMS = {
    "monto": ["nMonto"],
    "monto_desembolsado": ["nMonto"],
    "region": ["cRegion"],
    "región": ["cRegion"],
    "producto": ["cProducto"],
    "oficina": ["cOficina"],
    "ncosecha": ["nCosecha"],
    "nstock": ["nStock"],
    "idcliente": ["idCliente"],
    "idcuenta": ["idCuenta"],
}

def _map_field(field_norm: str, allowed_cols: Set[str], defaults: Set[str]) -> Optional[str]:
    """
    Mapea field_norm usando:
    1) allowed_cols (catálogo)
    2) defaults (solo si allowed_cols vacío)
    """
    if not field_norm:
        return None

    cols = allowed_cols if allowed_cols else defaults
    if not cols:
        return None

    # match directo
    for c in cols:
        if c.lower() == field_norm.lower():
            return c

    # sinónimos
    for cand in _FIELD_SYNONYMS.get(field_norm.lower(), []):
        if cand in cols:
            return cand

    # heurística token
    token = field_norm.lower()
    cands = [c for c in cols if token in c.lower()]
    if len(cands) == 1:
        return cands[0]

    return None


def _sql_literal(v: Any) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace("'", "''")
    return f"'{s}'"


def _build_filter_condition(f: Dict[str, Any], allowed_cols: Set[str], defaults: Set[str]) -> Optional[str]:
    field_norm = (f.get("field_norm") or f.get("field") or "").strip().lower()
    op = (f.get("operator") or "=").strip()
    val = f.get("value")

    col = _map_field(field_norm, allowed_cols, defaults)
    if not col:
        return None

    # "=" con texto => LIKE (general)
    if op == "=" and isinstance(val, str):
        vv = val.strip()
        if not re.fullmatch(r"\d+(\.\d+)?", vv) and len(vv) >= 3:
            op = "LIKE"
            val = f"%{vv}%"

    if op.upper() == "LIKE":
        return f"{col} LIKE {_sql_literal(val)}"
    return f"{col} {op} {_sql_literal(val)}"


def _fallback_sql(norm: Dict[str, Any], plan: Dict[str, Any], allowed_cols: Set[str]) -> str:
    """
    Fallback determinista robusto:
    - si allowed_cols está vacío, usa defaults por base_table
    - para ratio/percent escalar: CASE WHEN (filters) / total
    """
    inp = norm.get("input") or {}
    metric = inp.get("metric") or {}
    agg = (metric.get("aggregation") or {})
    agg_key = (agg.get("key") or agg.get("type") or "unknown").strip().lower()

    result_shape = (plan.get("result_shape") or "scalar").lower()
    from_sql = plan.get("from_sql") or ""
    where_sql = (plan.get("where_sql") or "").strip()

    base_table = plan.get("base_table") or ""
    defaults = _default_cols_for_base_table(base_table)

    measure = _map_field("monto", allowed_cols, defaults)
    if not measure:
        # si igual no hay medida, usamos COUNT(*) (no es perfecto para porcentaje de monto, pero es consistente)
        measure = None

    filters = inp.get("filters") or []
    conds = []
    for f in filters:
        if isinstance(f, dict):
            c = _build_filter_condition(f, allowed_cols, defaults)
            if c:
                conds.append(c)
    cond_sql = " AND ".join(conds) if conds else None

    # ratio/percent scalar
    if agg_key in ("ratio", "percent") and result_shape == "scalar":
        if measure:
            if cond_sql:
                numer = f"SUM(CASE WHEN {cond_sql} THEN {measure} ELSE 0 END)"
            else:
                numer = f"SUM({measure})"
            den = f"SUM({measure})"
            select_sql = (
                "SELECT ROUND("
                f"{numer} * 100.0 / NULLIF({den}, 0),"
                " 2) AS Resultado"
            )
        else:
            # sin columna de monto => porcentaje de conteo (general y seguro)
            if cond_sql:
                numer = f"SUM(CASE WHEN {cond_sql} THEN 1 ELSE 0 END)"
            else:
                numer = "COUNT(*)"
            den = "COUNT(*)"
            select_sql = (
                "SELECT ROUND("
                f"{numer} * 100.0 / NULLIF({den}, 0),"
                " 2) AS Resultado"
            )
        return f"{select_sql}\n{from_sql}\n{where_sql}".strip()

    # fallback general (sum)
    if measure:
        select_sql = f"SELECT SUM({measure}) AS Resultado"
    else:
        select_sql = "SELECT COUNT(*) AS Resultado"

    return f"{select_sql}\n{from_sql}\n{where_sql}".strip()


def _call_model_with_retry(prompt: str) -> str:
    # opts1 = {
    #     "temperature": 0,
    #     "num_predict": 192,
    #     "top_p": 0.9,
    #     "stop": ["```", "Para ", "En este", "Explicación", "Explanation:"],
    # }
    # try:
    #     resp = call_ollama(MODEL, prompt, timeout_seconds=180, options=opts1)
    #     return (resp.get("message", {}) or {}).get("content", "") or ""
    # except TimeoutError:
    #     print("[LLM] Ollama timeout. Retrying with longer timeout + smaller num_predict", flush=True)
    #     opts2 = dict(opts1)
    #     opts2["num_predict"] = 128
    #     resp2 = call_ollama(MODEL, prompt, timeout_seconds=360, options=opts2)
    #     return (resp2.get("message", {}) or {}).get("content", "") or ""
    messages = [{"role": "user", "content": prompt}]
    try:
        raw = generate_response(messages=messages, model_type="sql")
        return raw or ""
    except Exception as e:
        print(f"[LLM ERROR] Qwen falló en el primer intento: {e}. Reintentando...", flush=True)
        try:
            raw_retry = generate_response(messages=messages, model_type="sql")
            return raw_retry or ""
        except Exception as e2:
            print(f"[LLM ERROR FATAL] Qwen falló en el reintento: {e2}. Forzando error de tiempo.", flush=True)
            raise TimeoutError("Qwen Engine falló repetidamente.")

def create_sql_LLM(payload: Dict[str, Any], catalog, id_cliente) -> Tuple[str, str]:
    print("[LLM] enter create_sql_LLM", flush=True)

    norm = normalize_for_llm(payload)
    question = norm.get("question") or ""
    qsrc = norm.get("question_source") or "unknown"
    print(f"[LLM] question(source={qsrc})={question}", flush=True)

    plan = plan_query(norm, id_cliente=id_cliente)
    base_table = plan.get("base_table") or ""
    result_shape = plan.get("result_shape") or "scalar"

    allowed_cols = _allowed_cols_from_catalog(catalog, base_table)

    print("[LLM] Build SQL prompt", flush=True)
    prompt = build_sql_prompt(norm, plan, allowed_columns=sorted(list(allowed_cols)))

    preamble = (plan.get("preamble_sql") or "").strip()

    # LLM + retry, y si falla => fallback
    try:
        raw = _call_model_with_retry(prompt)
        sql_generated = _clean_llm_output(raw)
        sql_final = (preamble + "\n" + sql_generated).strip() if preamble else sql_generated
    except TimeoutError:
        print("[LLM] Qwen timeout even after retry. Using deterministic fallback", flush=True)
        sql_fb = _fallback_sql(norm, plan, allowed_cols)
        sql_final = (preamble + "\n" + sql_fb).strip() if preamble else sql_fb

    # Si no termina en SELECT => fallback
    if not _ends_with_select_query(sql_final):
        print("[LLM] output does not end with SELECT; using deterministic fallback", flush=True)
        sql_fb = _fallback_sql(norm, plan, allowed_cols)
        sql_final = (preamble + "\n" + sql_fb).strip() if preamble else sql_fb

    safety = is_safe_sql(sql_final)
    if not safety["ok"]:
        raise ValueError(f"SQL bloqueado: {safety['reason']}")
    
    if "group by" in sql_final.lower() and result_shape == "scalar":
        print("[LLM] Qwen aplicó GROUP BY correctamente. Ajustando result_shape a 'grouped'.", flush=True)
        result_shape = "grouped"

    vr = validate_sql_reasoning(sql_final, allowed_cols, result_shape=result_shape)
    if not vr["ok"]:
        print(f"[LLM] Error de razonamiento detectado: {vr['issues']}. Enviando Fix Prompt.", flush=True)
        plan_view = {
            "base_table": base_table,
            "result_shape": result_shape,
            "from_sql": plan.get("from_sql"),
            "where_sql": plan.get("where_sql"),
            "group_by_fields": plan.get("group_by_fields"),
            "notes": plan.get("notes"),
        }
        fix_prompt = build_fix_prompt(sql_final, vr["issues"], plan_view, sorted(list(allowed_cols)))

        try:
            raw2 = _call_model_with_retry(fix_prompt)
            sql_generated2 = _clean_llm_output(raw2)
            sql_final2 = (preamble + "\n" + sql_generated2).strip() if preamble else sql_generated2
        except TimeoutError:
            print("[LLM] Fix timeout. Using deterministic fallback", flush=True)
            sql_fb = _fallback_sql(norm, plan, allowed_cols)
            sql_final2 = (preamble + "\n" + sql_fb).strip() if preamble else sql_fb

        if not _ends_with_select_query(sql_final2):
            print("[LLM] fix output does not end with SELECT; using deterministic fallback", flush=True)
            sql_fb = _fallback_sql(norm, plan, allowed_cols)
            sql_final2 = (preamble + "\n" + sql_fb).strip() if preamble else sql_fb

        safety2 = is_safe_sql(sql_final2)
        if not safety2["ok"]:
            raise ValueError(f"SQL bloqueado en retry: {safety2['reason']}")

        vr2 = validate_sql_reasoning(sql_final2, allowed_cols, result_shape=result_shape)
        if not vr2["ok"]:
            raise ValueError(f"SQL inválido tras retry: {vr2['error']}")

        sql_final = sql_final2

    mode = "table" if result_shape in ("grouped", "series", "detail") else "scalar"
    print("[LLM] done create_sql_LLM", flush=True)
    return sql_final, mode
