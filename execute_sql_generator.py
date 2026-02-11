"""
execute_sql_generator.py

Módulo principal para generar SQL basado en intent y catalog, y ejecutarlo automáticamente en SQL Server.
Incluye:
- Planner determinista con preamble_sql (DECLARE/CTE)
- Inyección de IdCliente (desde payload.params o intent_json)
- Safety gate
- Ejecución scalar/table
- Guardado doble:
  1) Histórico: outputs/out_datos_YYYYMMDD_HHMMSS.json
  2) Último:   outputs/out_datos.json (se sobreescribe siempre)
"""

from __future__ import annotations

from typing import Any, Dict
import json
import os
from datetime import datetime

from loaders.json_loader import load_json_file
from engines.ollama_engine import call_ollama
from schemas.payloads import AgentPayload

from planners.intent_planner import plan_query
from prompts.sql_prompt_builder import build_sql_prompt
from utils.sql_safety import is_safe_sql
from executors.sql_server_executor import execute_sql
from decimal import Decimal, ROUND_HALF_UP

MODEL = "mistral:latest"


def _extract_id_cliente(intent_json_str: str, payload_params: Dict[str, Any]) -> int | None:
    """
    Prioridad:
    1) payload.params["IdCliente"]
    2) intent_json.intent_plan.tasks[0].input.scope.id
    3) intent_json.params.IdCliente   (si decides agregarlo al intent_json.json)
    """
    try:
        if payload_params and payload_params.get("IdCliente") is not None:
            return int(payload_params["IdCliente"])

        intent = json.loads(intent_json_str)

        tasks = intent.get("intent_plan", {}).get("tasks") or []
        if tasks:
            inp = tasks[0].get("input", {}) or {}
            scope = inp.get("scope", {}) or {}
            if scope.get("id") is not None:
                return int(scope["id"])

        intent_params = intent.get("params", {}) or {}
        if intent_params.get("IdCliente") is not None:
            return int(intent_params["IdCliente"])

        return None
    except Exception:
        return None

def _round_money(value: Any, decimals: int = 2) -> Any:
    # Redondeo estable (evita 0.26999997)
    if isinstance(value, float):
        q = Decimal("1." + ("0" * decimals))
        return float(Decimal(str(value)).quantize(q, rounding=ROUND_HALF_UP))
    return value

def build_clean_output(execution_result: Dict[str, Any], sql_final: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    if execution_result.get("status") != "success":
        return {"status": "error", "error": execution_result.get("error")}

    if "result" in execution_result:
        raw_val = execution_result.get("result")
        # Redondea SOLO si es float (scalar)
        val = _round_money(raw_val, 2)
        payload: Dict[str, Any] = {"type": "scalar", "data": val}
    else:
        payload = {
            "type": "table",
            "columns": execution_result.get("columns", []),
            "rows": execution_result.get("rows", []),
        }

    payload["metadata"] = {
        "timestamp": datetime.now().isoformat(),
        "sql_executed": execution_result.get("sql_executed", sql_final),
        "plan": plan,
    }
    return payload

def save_outputs(output_data: Dict[str, Any], output_dir: str = "outputs") -> Dict[str, str]:
    """
    Guarda:
    1) Histórico con timestamp: out_datos_YYYYMMDD_HHMMSS.json
    2) Último resultado: out_datos.json (se sobreescribe)
    Retorna rutas creadas.
    """
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    historical_path = os.path.join(output_dir, f"out_datos_{timestamp}.json")
    latest_path = os.path.join(output_dir, "out_datos.json")

    with open(historical_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    return {"historical": historical_path, "latest": latest_path}


def process(payload: AgentPayload) -> Dict[str, Any]:
    try:
        if payload.get("action") != "generate_sql":
            return {"status": "error", "error": "Solo se soporta action='generate_sql'."}

        intent_path = payload.get("intent_path")
        catalog_path = payload.get("catalog_path")
        params = payload.get("params", {}) or {}

        if not intent_path or not catalog_path:
            return {"status": "error", "error": "Falta intent_path o catalog_path."}

        intent_json = load_json_file(intent_path)
        _tables_catalog = load_json_file(catalog_path)  # reservado para validaciones futuras

        # IdCliente (si aplica)
        id_cliente = _extract_id_cliente(intent_json, params)

        # 1) Plan determinista (incluye preamble_sql: DECLARE/CTE)
        plan = plan_query(intent_json, id_cliente=id_cliente)

        # 2) Prompt
        prompt = build_sql_prompt(intent_json, plan)

        # 3) LLM: genera SOLO SELECT final
        response = call_ollama(MODEL, prompt)
        sql_generated = response["message"]["content"].strip()

        # 4) Ensamble final: preamble + SELECT
        preamble = (plan.get("preamble_sql") or "").strip()
        sql_final = (preamble + "\n" + sql_generated).strip() if preamble else sql_generated

        # 5) Safety gate (sobre SQL final)
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
            mode = "table" if plan.get("result_shape") in ("grouped", "series", "detail") else "scalar"

        execution_result = execute_sql(sql_final, mode=mode)

        return {
            "status": "success",
            "plan": plan,
            "sql_generated": sql_generated,  # solo SELECT
            "sql_final": sql_final,          # preamble + SELECT
            "execution_result": execution_result,
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    test_payload: AgentPayload = {
        "action": "generate_sql",
        "intent_path": "intent_json.json",
        "catalog_path": "tables_catalog.json",
        "params": {
            # Si haces consultas tipo "mi ..." pon IdCliente aquí
            # "IdCliente": 15675
        },
    }

    result = process(test_payload)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Guardar outputs (histórico + último)
    if result.get("status") == "success":
        exec_res = result.get("execution_result", {})
        if exec_res.get("status") == "success":
            output_data = build_clean_output(
                execution_result=exec_res,
                sql_final=result.get("sql_final", ""),
                plan=result.get("plan", {}),
            )
            paths = save_outputs(output_data)

            print(f"[INFO] Histórico guardado en: {paths['historical']}")
            print(f"[INFO] Último resultado actualizado en: {paths['latest']}")
        else:
            print("[WARNING] Error ejecutando SQL; no se guarda archivo.")
    else:
        print("[ERROR] Falló la generación del SQL; no se guarda archivo.")
