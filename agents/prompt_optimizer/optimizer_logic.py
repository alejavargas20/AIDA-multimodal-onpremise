from __future__ import annotations

import json
import os
import re

from typing import Any, Dict, List

from pydantic import ValidationError as PydanticValidationError

from .baseline import baseline_intent, baseline_action_stub
from .exceptions import ValidationError  # error propio (para serialización, etc.)
from .preprocessing import preprocess
from .schema import PromptOptimizerResponse, IntentPlan, Task

from .llm_client import call_llm_chat
from .planner_prompt import PLANNER_SYSTEM_PROMPT

def _extract_json_object(text: str) -> Dict[str, Any]:
    """
    Extracts a JSON object from model output.
    Strict: returns dict or raises ValueError.
    """
    t = (text or "").strip()

    # First try direct parse
    try:
        obj = json.loads(t)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Try to extract first {...} block
    m = re.search(r"\{.*\}", t, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in LLM output.")

    candidate = m.group(0).strip()
    obj2 = json.loads(candidate)
    if not isinstance(obj2, dict):
        raise ValueError("LLM output JSON is not an object.")
    return obj2


def _llm_messages(system_prompt: str, user_text: str, metadata: Dict[str, Any]) -> List[Dict[str, str]]:
    # Keep it minimal: system + user
    user_payload = {
        "user_text": user_text,
        "metadata": metadata,
        "constraints": {"output_format": "json_only", "max_tasks": 3},
    }
    return [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]

def _normalize_plan_for_nlp(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aligns LLM output with NLP agent contract (Naty):
    - NLP action must be one of: summarize, explain, rephrase, reason, generate
    - NLP input must be a dict
    - map legacy actions (answer -> reason, ask_clarification -> reason or remove)
    """
    supported = {"summarize", "explain", "rephrase", "reason", "generate"}
    action_map = {
        "answer": "reason",
        "ask_clarification": None,  # we should not route clarifications to NLP
    }

    tasks = (plan.get("intent_plan", {}) or {}).get("tasks", [])
    if not isinstance(tasks, list):
        return plan

    normalized_tasks = []
    for t in tasks:
        if not isinstance(t, dict):
            continue

        agent = (t.get("agent") or "").strip().lower()
        action = (t.get("action") or "").strip().lower()
        inp = t.get("input")

        if agent == "nlp":
            if action in action_map:
                action = action_map[action]
                if action is None:
                    # drop this task
                    continue

            if action not in supported:
                # fallback safest: reason
                action = "reason"

            if isinstance(inp, str):
                # convert to dict expected by NLP
                if action == "summarize":
                    inp = {"text": inp}
                elif action == "explain":
                    inp = {"question": inp}
                elif action == "rephrase":
                    inp = {"text": inp}
                elif action == "generate":
                    inp = {"instructions": inp}
                else:
                    inp = {"question": inp}

            if inp is None or not isinstance(inp, dict):
                inp = {"question": "Falta input estructurado; usar la petición original como fallback."}

            t["action"] = action
            t["input"] = inp

        normalized_tasks.append(t)

    plan["intent_plan"]["tasks"] = normalized_tasks[:3]
    return plan


def _build_tasks(intent: str, user_text: str) -> List[Task]:
    stub = baseline_action_stub(intent)
    agent = stub["agent"]
    action = stub["action"]

    # Keep input business-level (NO SQL)
    if agent == "data":
        task_input = f"Consulta agregada relacionada con: {intent}. Contexto: {user_text}"
    elif agent == "image":
        task_input = {"source": "document", "mode": "normalized_text"}
    else:
        task_input = {
            "text": user_text,
            "style": "ejecutivo",
            "audience": "general",
            "constraints": {"length": "short"}
        }

    return [
        Task(
            agent=agent,  # type: ignore[arg-type]
            action=action,
            input=task_input,
            params={},
        )
    ]


def process_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Public stable function to be called by MCP tool layer.
    Must return JSON-serializable dict only (no text outside JSON).
    """
    fase1 = preprocess(payload)
    user_text = fase1["user_text"]
    language = fase1["language"]
    input_source = fase1["input_source"]

    metadata = {"language": language, "input_source": input_source}

    # Baseline intent (LLM planner can be plugged later)
    intent, base_conf = baseline_intent(user_text)
    use_llm = os.getenv("USE_LLM_PLANNER", "true").lower() in ("1", "true", "yes", "y", "on")


    # Clarification guardrail (very short/empty)
    if not user_text or len(user_text) < 4:
        response = PromptOptimizerResponse(
            optimized_prompt="Necesito más contexto para planificar la petición.",
            intent_plan=IntentPlan(
                intent="otro_ayuda",
                confidence=0.2,
                tasks=[],
                metadata=metadata,
                conductual_state=None,
                conductual_notes="Input demasiado corto o vacío.",
            ),
            status="needs_clarification",
            errors=["Input demasiado corto para planificar."],
        )
        return response.model_dump()

    # Guardrail explícito: SQL detectado → no construir tasks
    lowered = user_text.lower()
    if any(k in lowered for k in ["select ", " from ", " join ", " where ", " group by", "insert ", "update ", "delete "]):
        safe_response = {
            "optimized_prompt": (
                "Reformula la petición sin incluir SQL ni nombres de tablas. "
                "Indica el objetivo de negocio (qué quieres analizar) y el periodo."
            ),
            "intent_plan": {
                "intent": "needs_clarification",
                "confidence": 0.0,
                "tasks": [],
                "metadata": metadata,
                "conductual_state": None,
                "conductual_notes": "Entrada contenía SQL u otro patrón no permitido.",
            },
            "status": "needs_clarification",
            "errors": [],
        }

        json.dumps(safe_response)
        return safe_response
    
    
    try:
        # 1) Try LLM planner (as per Desarrollo: Prompt Optimizer uses Llama 3)
        if use_llm:
            metadata_for_llm = {"language": language, "input_source": input_source}
            messages = _llm_messages(PLANNER_SYSTEM_PROMPT, user_text, metadata_for_llm)

            last_err = None
            for attempt in range(2):  # retry up to 2 attempts
                try:
                    raw = call_llm_chat(messages)
                    plan_dict = _extract_json_object(raw)
                    plan_dict = _normalize_plan_for_nlp(plan_dict)

                    # Enforce max_tasks defensively (also enforced by schema max_length=3)
                    tasks_list = plan_dict.get("intent_plan", {}).get("tasks", [])
                    if isinstance(tasks_list, list) and len(tasks_list) > 3:
                        plan_dict["intent_plan"]["tasks"] = tasks_list[:3]

                    # Validate strictly with Pydantic schema
                    validated = PromptOptimizerResponse.model_validate(plan_dict)
                    data = validated.model_dump()

                    try:
                        tasks_list = data.get("intent_plan", {}).get("tasks", []) or []
                        if isinstance(tasks_list, list):
                            metric = None
                            period = None
                            for t in tasks_list:
                                if isinstance(t, dict) and (t.get("agent") == "data") and (t.get("action") == "fetch_metrics"):
                                    inp = t.get("input") or {}
                                    if isinstance(inp, dict):
                                        metric = inp.get("metric")
                                        period = inp.get("period")

                            if metric and period:
                                data["optimized_prompt"] = f"Resume de forma ejecutiva las {metric} del {period}."
                            else:
                                data["optimized_prompt"] = user_text
                    except Exception:
                        data["optimized_prompt"] = user_text

                    json.dumps(data)
                    return data

                except Exception as e:
                    last_err = e
                    # Ask the LLM to correct its output to strict JSON-only
                    messages = [
                        {"role": "system", "content": PLANNER_SYSTEM_PROMPT.strip()},
                        {
                            "role": "user",
                            "content": (
                                "Your previous output was invalid. Return ONLY valid JSON matching the required schema. "
                                "Do not include any extra text.\n\n"
                                f"Validation error: {type(last_err).__name__}: {last_err}\n\n"
                                f"User request: {user_text}"
                            ),
                        },
                    ]
            # If LLM failed after retries, fallback
            # (We'll continue to baseline below.)
            pass


        # 2) Baseline fallback (keeps system resilient)
        tasks = _build_tasks(intent, user_text)

        response = PromptOptimizerResponse(
            optimized_prompt=user_text,
            intent_plan=IntentPlan(
                intent=intent,
                confidence=base_conf,
                tasks=tasks,
                metadata=metadata,
                conductual_state=None,
                conductual_notes=None,
            ),
            status="ok",
            errors=[],
        )

        data = response.model_dump()
        json.dumps(data)
        return data


    except PydanticValidationError as e:
        # Si el usuario mete SQL u otro patrón prohibido,
        # el Prompt Optimizer NO debe explotar: devuelve plan seguro y pide reformulación.
        safe_response = {
            "optimized_prompt": (
                "Reformula la petición sin incluir SQL ni nombres de tablas. "
                "Indica el objetivo de negocio (qué quieres analizar) y el periodo."
            ),
            "intent_plan": {
                "intent": "needs_clarification",
                "confidence": 0.0,
                "tasks": [],
                "metadata": metadata,
                "conductual_state": None,
                "conductual_notes": "Entrada contenía SQL u otro patrón no permitido.",
            },
            "status": "needs_clarification",
            "errors": [],
        }

        # Garantizamos serialización también aquí
        try:
            json.dumps(safe_response)
        except Exception as exc:
            raise ValidationError(f"Safe response not JSON-serializable: {exc}") from exc

        return safe_response

    except Exception as exc:
        # Fallo inesperado controlado: no rompemos el sistema.
        safe_error = {
            "optimized_prompt": "Se produjo un error al planificar la petición.",
            "intent_plan": {
                "intent": "error",
                "confidence": 0.0,
                "tasks": [],
                "metadata": metadata,
                "conductual_state": None,
                "conductual_notes": "Error interno no esperado.",
            },
            "status": "error",
            "errors": [str(exc)],
        }

        try:
            json.dumps(safe_error)
        except Exception as exc2:
            raise ValidationError(f"Error response not JSON-serializable: {exc2}") from exc2

        return safe_error
