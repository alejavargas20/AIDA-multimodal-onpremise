# # agents/data/LLM_logic/main_LLM.py
# from __future__ import annotations
# from typing import Dict, Any, Tuple, Set

# from agents.data.LLM_logic.utils import _extract_id_cliente, is_safe_sql
# from agents.data.LLM_logic.planners.intent_planner import plan_query
# from agents.data.LLM_logic.prompts.sql_prompt_builder import build_sql_prompt
# from agents.data.LLM_logic.engines.ollama_engine import call_ollama
# from agents.data.LLM_logic.normalize_intent import normalize_for_llm
# from agents.data.LLM_logic.validators.sql_validator import (
#     build_catalog_index,
#     resolve_table_key,
#     validate_sql_reasoning,
#     build_fix_prompt,
# )

# MODEL = "mistral:latest"


# def _clean_llm_output(text: str) -> str:
#     if not text:
#         return ""
#     t = text.strip()

#     # elimina fences
#     if "```" in t:
#         parts = t.split("```")
#         candidate = ""
#         for p in parts:
#             if "select" in p.lower():
#                 candidate = p
#                 break
#         t = candidate.strip() if candidate else t.replace("```", "").strip()

#     # corta antes del SELECT
#     lo = t.lower()
#     idx = lo.find("select")
#     if idx >= 0:
#         t = t[idx:].strip()

#     return t


# def _allowed_cols_from_catalog(catalog: Any, base_table: str) -> Set[str]:
#     catalog_idx = build_catalog_index(catalog)
#     key = resolve_table_key(base_table, catalog_idx) or base_table
#     return set(catalog_idx.get(key) or set())


# def create_sql_LLM(payload: Dict[str, Any], catalog, id_cliente) -> Tuple[str, str]:
#     print("[LLM] enter create_sql_LLM", flush=True)

#     norm = normalize_for_llm(payload)
#     intent = norm["raw"]
#     params = norm["params"]
#     question = norm["question"]

#     plan = plan_query(norm, id_cliente=id_cliente)
#     base_table = plan.get("base_table") or ""
#     result_shape = plan.get("result_shape") or "scalar"

#     allowed_cols = _allowed_cols_from_catalog(catalog, base_table)

#     print("[LLM] Build SQL prompt", flush=True)
#     print("[LLM] question=", question, flush=True)

#     prompt = build_sql_prompt(norm, plan, allowed_columns=sorted(list(allowed_cols)))

#     ollama_options = {
#         "temperature": 0,
#         "num_predict": 256,
#         "stop": ["```", "Para ", "En este", "Explicación", "Explanation:"],
#     }

#     # 1) generación
#     resp = call_ollama(MODEL, prompt, timeout_seconds=180, options=ollama_options)
#     raw = (resp.get("message", {}) or {}).get("content", "")
#     sql_generated = _clean_llm_output(raw)

#     preamble = (plan.get("preamble_sql") or "").strip()
#     sql_final = (preamble + "\n" + sql_generated).strip() if preamble else sql_generated

#     safety = is_safe_sql(sql_final)
#     if not safety["ok"]:
#         raise ValueError(f"SQL bloqueado: {safety['reason']}")

#     vr = validate_sql_reasoning(sql_final, allowed_cols, result_shape=result_shape)

#     if not vr["ok"]:
#         plan_view = {
#             "base_table": base_table,
#             "result_shape": result_shape,
#             "from_sql": plan.get("from_sql"),
#             "where_sql": plan.get("where_sql"),
#             "group_by_fields": plan.get("group_by_fields"),
#             "notes": plan.get("notes"),
#         }
#         fix_prompt = build_fix_prompt(
#             sql_final,
#             vr["issues"],
#             plan_view,
#             sorted(list(allowed_cols)),
#         )

#         # 2) retry único
#         resp2 = call_ollama(MODEL, fix_prompt, timeout_seconds=180, options=ollama_options)
#         raw2 = (resp2.get("message", {}) or {}).get("content", "")
#         sql_generated2 = _clean_llm_output(raw2)

#         sql_final2 = (preamble + "\n" + sql_generated2).strip() if preamble else sql_generated2

#         safety2 = is_safe_sql(sql_final2)
#         if not safety2["ok"]:
#             raise ValueError(f"SQL bloqueado en retry: {safety2['reason']}")

#         vr2 = validate_sql_reasoning(sql_final2, allowed_cols, result_shape=result_shape)
#         if not vr2["ok"]:
#             raise ValueError(f"SQL inválido tras retry: {vr2['error']}")

#         sql_final = sql_final2

#     mode = params.get("mode")
#     if not mode:
#         mode = "table" if result_shape in ("grouped", "series", "detail") else "scalar"

#     print("[LLM] done create_sql_LLM", flush=True)
#     return sql_final, mode



from __future__ import annotations
from typing import Dict, Any, Tuple, Set

from agents.data.LLM_logic.utils import _extract_id_cliente, is_safe_sql
from agents.data.LLM_logic.planners.intent_planner import plan_query
from agents.data.LLM_logic.prompts.sql_prompt_builder import build_sql_prompt
from agents.data.LLM_logic.normalize_intent import normalize_for_llm
from agents.data.LLM_logic.validators.sql_validator import (
    build_catalog_index,
    resolve_table_key,
    validate_sql_reasoning,
    build_fix_prompt,
)

# Importamos nuestro poderoso motor híbrido Qwen en lugar de Ollama
from agents.local_engine import generate_response

def _clean_llm_output(text: str) -> str:
    if not text:
        return ""
    t = text.strip()

    # elimina fences
    if "```" in t:
        parts = t.split("```")
        candidate = ""
        for p in parts:
            if "select" in p.lower():
                candidate = p
                break
        t = candidate.strip() if candidate else t.replace("```", "").strip()

    # corta antes del SELECT
    lo = t.lower()
    idx = lo.find("select")
    if idx >= 0:
        t = t[idx:].strip()

    return t


def _allowed_cols_from_catalog(catalog: Any, base_table: str) -> Set[str]:
    catalog_idx = build_catalog_index(catalog)
    key = resolve_table_key(base_table, catalog_idx) or base_table
    return set(catalog_idx.get(key) or set())


def create_sql_LLM(payload: Dict[str, Any], catalog, id_cliente) -> Tuple[str, str]:
    print("[LLM] enter create_sql_LLM", flush=True)

    norm = normalize_for_llm(payload)
    intent = norm["raw"]
    params = norm["params"]
    question = norm["question"]

    plan = plan_query(norm, id_cliente=id_cliente)
    base_table = plan.get("base_table") or ""
    result_shape = plan.get("result_shape") or "scalar"

    allowed_cols = _allowed_cols_from_catalog(catalog, base_table)

    print("[LLM] Build SQL prompt", flush=True)
    print("[LLM] question=", question, flush=True)

    prompt = build_sql_prompt(norm, plan, allowed_columns=sorted(list(allowed_cols)))

    # 1) GENERACIÓN PRIMARIA (USANDO QWEN LOCAL_ENGINE)
    print("[DATA] Generando SQL con Qwen 2.5 (Intento 1)")
    messages = [{"role": "user", "content": prompt}]
    raw = generate_response(messages=messages, model_type="sql")
    
    sql_generated = _clean_llm_output(raw)

    preamble = (plan.get("preamble_sql") or "").strip()
    sql_final = (preamble + "\n" + sql_generated).strip() if preamble else sql_generated

    safety = is_safe_sql(sql_final)
    if not safety["ok"]:
        raise ValueError(f"SQL bloqueado: {safety['reason']}")

    vr = validate_sql_reasoning(sql_final, allowed_cols, result_shape=result_shape)

    # 2) AUTO-CORRECCIÓN (SI QWEN SE EQUIVOCÓ)

    if not vr["ok"]:
        print(f"[DATA] SQL Inválido detectado. Iniciando Auto-Corrección. Motivo: {vr['issues']}")
        plan_view = {
            "base_table": base_table,
            "result_shape": result_shape,
            "from_sql": plan.get("from_sql"),
            "where_sql": plan.get("where_sql"),
            "group_by_fields": plan.get("group_by_fields"),
            "notes": plan.get("notes"),
        }
        fix_prompt = build_fix_prompt(
            sql_final,
            vr["issues"],
            plan_view,
            sorted(list(allowed_cols)),
        )

        print("[DATA] Generando corrección SQL con Qwen 2.5 (Intento 2)")
        messages_retry = [{"role": "user", "content": fix_prompt}]
        raw2 = generate_response(messages=messages_retry, model_type="sql")
        
        sql_generated2 = _clean_llm_output(raw2)

        sql_final2 = (preamble + "\n" + sql_generated2).strip() if preamble else sql_generated2

        safety2 = is_safe_sql(sql_final2)
        if not safety2["ok"]:
            raise ValueError(f"SQL bloqueado en retry: {safety2['reason']}")

        vr2 = validate_sql_reasoning(sql_final2, allowed_cols, result_shape=result_shape)
        if not vr2["ok"]:
            raise ValueError(f"SQL inválido tras retry: {vr2['error']}")

        sql_final = sql_final2

    mode = params.get("mode")
    if not mode:
        mode = "table" if result_shape in ("grouped", "series", "detail") else "scalar"

    print("[LLM] done create_sql_LLM", flush=True)
    return sql_final, mode