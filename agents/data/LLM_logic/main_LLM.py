# aida-multimodal-onpremise/agents/data/LLM_logic/main_LLM.py

from agents.data.LLM_logic.utils import _extract_id_cliente, is_safe_sql
from agents.data.LLM_logic.planners.intent_planner import plan_query
from agents.data.LLM_logic.prompts.sql_prompt_builder import build_sql_prompt
#from agents.data.LLM_logic.engines.ollama_engine import call_ollama
from agents.local_engine import generate_response

def create_sql_LLM(intent_json, catalog, id_cliente):

    params = intent_json.get("params", {}) or {}

    # 1) Plan determinista (incluye preamble_sql: DECLARE/CTE)
    print("Plan Query")
    plan = plan_query(intent_json, id_cliente=id_cliente)

    # 2) Prompt
    print("Build SQL")
    prompt = build_sql_prompt(intent_json, plan)

    # 3) LLM: genera SOLO SELECT final
    # MODEL = "mistral:latest"
    # print("call ollama")
    # print(prompt)
    # response = call_ollama(MODEL, prompt)
    # sql_generated = response["message"]["content"].strip()

    print("[DATA] Generando SQL con Qwen 2.5")
    # Preparamos el mensaje en el formato que espera tu HybridEngine
    messages = [{"role": "user", "content": prompt}]
    # Llamamos a Qwen 2.5 (model_type="sql") y obtenemos el SQL generado
    sql_generated = generate_response(messages=messages, model_type="sql").strip()

    # 4) Ensamble final: preamble + SELECT
    print("preamble")
    preamble = (plan.get("preamble_sql") or "").strip()
    sql_final = (preamble + "\n" + sql_generated).strip() if preamble else sql_generated

    # 5) Safety gate (sobre SQL final)
    print("safety sql")
    safety = is_safe_sql(sql_final)
    if not safety["ok"]:
        return {
            "status": "error",
            "error": f"SQL bloqueado: {safety['reason']}",
            "sql_generated": sql_generated,
            "sql_final": sql_final,
            "plan": plan,
        }

    # 6) Ejecutar (scalar/table)
    mode = params.get("mode")
    if not mode:
        mode = (
            "table"
            if plan.get("result_shape") in ("grouped", "series", "detail")
            else "scalar"
        )

    return sql_final, mode
