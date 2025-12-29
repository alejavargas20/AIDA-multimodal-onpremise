from __future__ import annotations

import json
from typing import Any, Dict, List

from pydantic import ValidationError as PydanticValidationError

from .baseline import baseline_intent, baseline_action_stub
from .exceptions import ValidationError  # tu error propio (para serialización, etc.)
from .preprocessing import preprocess
from .schema import PromptOptimizerResponse, IntentPlan, Task


def _build_tasks(intent: str, user_text: str) -> List[Task]:
    stub = baseline_action_stub(intent)
    agent = stub["agent"]
    action = stub["action"]

    # Keep input business-level (NO SQL)
    if agent == "data":
        task_input = f"Consulta agregada relacionada con: {intent}. Contexto: {user_text}"
    elif agent == "image":
        task_input = "Extraer texto/estructura del documento para posterior análisis"
    else:
        # IMPORTANTE: aunque sea NLP, el Task.input no debe contener SQL.
        # Si el user_text trae SQL, el validador de Task lo bloqueará.
        task_input = f"Responder o resumir la petición: {user_text}"

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

    # --- NUEVO: robustez ante inputs inválidos (ej. SQL en el texto del usuario) ---
    try:
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

        # Validation: ensure JSON serializable
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
                "tasks": [
                    {
                        "agent": "nlp",
                        "action": "nlp.ask_clarification",
                        "input": (
                            "El usuario ha incluido SQL. Pedir reformulación a nivel de objetivo de negocio, sin SQL."
                        ),
                        "params": {},
                    }
                ],
                "metadata": metadata,
                "conductual_state": None,
                "conductual_notes": "Entrada contenía SQL u otro patrón no permitido.",
            },
            "status": "needs_clarification",
            "errors": [str(e)],
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
