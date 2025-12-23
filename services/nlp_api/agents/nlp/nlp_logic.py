from __future__ import annotations

import time
from typing import Any, Dict, Optional

from rag.rag_pipeline import answer_with_rag

SUPPORTED_TASKS = {
    "summarize",
    "explain",
    "respond",
    "rephrase",
    "classify",
    "extract_entities",
}


# Helpers de respuesta estándar 

def _ok(*, task: str, result: Dict[str, Any], language: str, input_source: str, t0: float) -> Dict[str, Any]:
    return {
        "ok": True,
        "task": task,
        "result": result,
        "metadata": {
            "language": language,
            "input_source": input_source,
            "processing_time_ms": int((time.perf_counter() - t0) * 1000),
        },
    }


def _error(
    *,
    task: Optional[str],
    language: str,
    input_source: str,
    t0: float,
    message: str
) -> Dict[str, Any]:
    return {
        "ok": False,
        "task": task,
        "error": {"message": message},
        "metadata": {
            "language": language,
            "input_source": input_source,
            "processing_time_ms": int((time.perf_counter() - t0) * 1000),
        },
    }


def _truncate(text: str, n: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[:n].rstrip() + "..."


# --------------------------
# ÚNICA FUNCIÓN PÚBLICA PARA MCP
# --------------------------

def process(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP/orquestador importará:
        from agents.nlp.nlp_logic import process
        process(payload) -> dict
    """
    t0 = time.perf_counter()

    task = payload.get("task")
    input_obj = payload.get("input", {}) or {}
    style = payload.get("style", "breve")
    metadata = payload.get("metadata", {}) or {}

    language = metadata.get("language", "es")
    input_source = metadata.get("input_source", "chat")

    # Validación de task
    if task not in SUPPORTED_TASKS:
        return _error(
            task=task,
            language=language,
            input_source=input_source,
            t0=t0,
            message=f"Unsupported NLP task: {task}. Supported: {sorted(SUPPORTED_TASKS)}",
        )

    # input.text obligatorio
    text = input_obj.get("text", "")
    if not isinstance(text, str) or not text.strip():
        return _error(
            task=task,
            language=language,
            input_source=input_source,
            t0=t0,
            message="Missing or empty input.text",
        )

    # Router
    try:
        if task == "respond":
            history = input_obj.get("history", None)
            retrieval = bool(input_obj.get("retrieval", True))
            top_k = input_obj.get("top_k", None)

            answer, used_docs, rag_elapsed_ms = answer_with_rag(
                question=text,
                history=history,
                retrieval=retrieval,
                top_k=top_k,
            )

            result = {
                "text": answer,
                "used_docs": used_docs,
                "rag_elapsed_ms": rag_elapsed_ms,
            }
            return _ok(task=task, result=result, language=language, input_source=input_source, t0=t0)

        if task == "summarize":
            return _ok(
                task=task,
                result={"text": _truncate(text, 400), "style": style},
                language=language,
                input_source=input_source,
                t0=t0,
            )

        if task == "explain":
            return _ok(
                task=task,
                result={"text": f"Explicación ({style}): {_truncate(text, 1200)}"},
                language=language,
                input_source=input_source,
                t0=t0,
            )

        if task == "rephrase":
            return _ok(
                task=task,
                result={"text": text.strip(), "style": style},
                language=language,
                input_source=input_source,
                t0=t0,
            )

        if task == "classify":
            return _ok(
                task=task,
                result={"label": "otro"},
                language=language,
                input_source=input_source,
                t0=t0,
            )

        if task == "extract_entities":
            return _ok(
                task=task,
                result={"dates": [], "amounts": [], "percentages": []},
                language=language,
                input_source=input_source,
                t0=t0,
            )

        # Si por alguna razón cae aquí:
        return _error(
            task=task,
            language=language,
            input_source=input_source,
            t0=t0,
            message=f"Task not implemented: {task}",
        )

    except Exception as e:
        return _error(
            task=task,
            language=language,
            input_source=input_source,
            t0=t0,
            message=f"Unhandled error: {type(e).__name__}: {e}",
        )

