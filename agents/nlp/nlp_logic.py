"""
Agente NLP (solo español)

Este módulo implementa UNA única función pública para ser llamada desde el MCP:
    from agents.nlp.nlp_logic import process
    process(payload: dict) -> dict

El orquestador decide qué hacer y envía en `payload["task"]` la acción a ejecutar.
"""

from __future__ import annotations

import os
import time
import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional, Tuple, List


# ---- Config (env) ----
DEFAULT_MODEL = os.getenv("NLP_MODEL", "llama3.2:3b")
DEFAULT_PROVIDER = os.getenv("NLP_PROVIDER", "ollama")  # "ollama" | "mock"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
REQUEST_TIMEOUT_S = float(os.getenv("NLP_REQUEST_TIMEOUT_S", "30"))


# ---- Public API ----
SUPPORTED_TASKS = {
    "summarize",
    "explain",
    "rephrase",
    "reason",
    "generate",
    "auto",
}


def process(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Punto de entrada único del Agente NLP.

    Payload esperado (mínimo):
    {
      "task": "summarize|explain|rephrase|reason|generate|auto",
      "input": {...},
      "style": "sencillo|tecnico|ejecutivo" (opcional),
      "metadata": {...} (opcional)
    }
    """
    t0 = time.time()

    if not isinstance(payload, dict):
        return _error("Payload must be a dict.", task=None, t0=t0)

    task = payload.get("task") or payload.get("action")  # compat
    if not task or not isinstance(task, str):
        return _error("Missing 'task' in payload.", task=None, t0=t0)

    task = task.strip().lower()
    if task not in SUPPORTED_TASKS:
        return _error(
            f"Unsupported NLP task: {task}. Supported: {sorted(SUPPORTED_TASKS)}",
            task=task,
            t0=t0,
        )

    input_obj = payload.get("input") or {}
    if not isinstance(input_obj, dict):
        return _error("payload.input must be an object/dict.", task=task, t0=t0)

    # Solo español (sin detección)
    language = "es"

    # Enrutamiento
    try:
        if task == "summarize":
            answer = summarize(input_obj, payload)
        elif task == "explain":
            answer = explain(input_obj, payload)
        elif task == "rephrase":
            answer = rephrase(input_obj, payload)
        elif task == "reason":
            answer = reason(input_obj, payload)
        elif task == "generate":
            answer = generate(input_obj, payload)
        elif task == "auto":
            # Modo "función general": decide handler según intent/topic/etc.
            routed_task, answer = auto_route(input_obj, payload)
            task = routed_task
        else:
            return _error("Task router reached unexpected state.", task=task, t0=t0)

        return _ok(task=task, answer=answer, language=language, t0=t0)

    except Exception as e:
        return _error(f"Unhandled error: {type(e).__name__}: {e}", task=task, t0=t0)


# ---- Internal task handlers ----

def summarize(input_obj: Dict[str, Any], payload: Dict[str, Any]) -> str:
    """
    Resume datos estructurados (p. ej. salida del Agente de Datos) o texto largo.
    Inputs:
      - data: dict|list (preferido)
      - text: str (alternativo)
      - audience: "analista"|"cliente"
      - style: "ejecutivo"|"tecnico"|"sencillo"
      - constraints: {"length": "short|medium", "format": "bullets|paragraph"}
    """
    audience, style, constraints = _normalize_style(input_obj, payload)

    data = input_obj.get("data")
    text = input_obj.get("text") or input_obj.get("question") or ""

    if data is None and (not isinstance(text, str) or not text.strip()):
        raise ValueError("summarize requires 'input.data' or non-empty 'input.text'.")

    user_goal = input_obj.get("goal") or "Resume la información principal."
    content_block = _render_content_block(data=data, text=text)

    system, user = _build_prompt(
        task="summarize",
        audience=audience,
        style=style,
        constraints=constraints,
        user_goal=user_goal,
        content=content_block,
    )
    return _llm_or_fallback(
        system,
        user,
        fallback=_fallback_summarize(data=data, text=text, audience=audience, style=style),
    )


def explain(input_obj: Dict[str, Any], payload: Dict[str, Any]) -> str:
    """
    Explica un concepto, una tabla/campo o un resultado.
    Inputs soportados:
      - concept: str  (ej: "saldo vencido", "días de mora")
      - table: {"name": "...", "description": "...", "fields": [...]}
      - field: {"name": "...", "description": "...", "table": "..."}
      - data: dict|list  (para explicar un resultado)
      - question: str    (pregunta del usuario)
      - audience/style/constraints (igual que summarize)
    """
    audience, style, constraints = _normalize_style(input_obj, payload)

    concept = input_obj.get("concept") or input_obj.get("topic")
    question = input_obj.get("question") or input_obj.get("text") or ""
    table = input_obj.get("table")
    field = input_obj.get("field")
    data = input_obj.get("data")

    if not any([concept, question, table, field, data]):
        raise ValueError(
            "explain requires at least one of: concept/topic, question/text, table, field, data."
        )

    user_goal = input_obj.get("goal") or "Explica claramente lo solicitado."
    content_block = _render_content_block(
        data=data, text=question, concept=concept, table=table, field=field
    )

    system, user = _build_prompt(
        task="explain",
        audience=audience,
        style=style,
        constraints=constraints,
        user_goal=user_goal,
        content=content_block,
    )
    return _llm_or_fallback(
        system,
        user,
        fallback=_fallback_explain(
            concept=concept,
            question=question,
            table=table,
            field=field,
            audience=audience,
            style=style,
        ),
    )


def rephrase(input_obj: Dict[str, Any], payload: Dict[str, Any]) -> str:
    """
    Reformula un texto en español ajustando estilo/audiencia.
    Input:
      - text: str (obligatorio)
      - audience/style/constraints
    """
    audience, style, constraints = _normalize_style(input_obj, payload)
    text = input_obj.get("text") or input_obj.get("question") or ""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("rephrase requires non-empty 'input.text'.")

    user_goal = input_obj.get("goal") or "Reformula el texto manteniendo el significado."
    content_block = _render_content_block(text=text)

    system, user = _build_prompt(
        task="rephrase",
        audience=audience,
        style=style,
        constraints=constraints,
        user_goal=user_goal,
        content=content_block,
    )
    return _llm_or_fallback(system, user, fallback=text.strip())


def reason(input_obj: Dict[str, Any], payload: Dict[str, Any]) -> str:
    """
    Responde a una pregunta o justifica una explicación.
    Input:
      - question: str (preferido) o text: str
      - context: str|list (opcional)
      - data: dict|list (opcional)
      - audience/style/constraints
    """
    audience, style, constraints = _normalize_style(input_obj, payload)

    question = input_obj.get("question") or input_obj.get("text") or ""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("reason requires non-empty 'input.question' (or 'input.text').")

    context = input_obj.get("context")
    data = input_obj.get("data")
    user_goal = input_obj.get("goal") or "Responde y justifica de forma clara."

    content_block = _render_content_block(text=question, data=data, context=context)

    system, user = _build_prompt(
        task="reason",
        audience=audience,
        style=style,
        constraints=constraints,
        user_goal=user_goal,
        content=content_block,
    )
    return _llm_or_fallback(system, user, fallback=_fallback_reason(question=question))


def generate(input_obj: Dict[str, Any], payload: Dict[str, Any]) -> str:
    """
    Genera un texto en español a partir de instrucciones y/o contexto.
    Input:
      - instructions: str (preferido) o prompt: str
      - context/data opcional
      - audience/style/constraints
    """
    audience, style, constraints = _normalize_style(input_obj, payload)
    instructions = input_obj.get("instructions") or input_obj.get("prompt") or ""
    if not isinstance(instructions, str) or not instructions.strip():
        raise ValueError("generate requires non-empty 'input.instructions' (or 'input.prompt').")

    context = input_obj.get("context")
    data = input_obj.get("data")
    user_goal = input_obj.get("goal") or "Genera el texto solicitado."

    content_block = _render_content_block(text=instructions, data=data, context=context)

    system, user = _build_prompt(
        task="generate",
        audience=audience,
        style=style,
        constraints=constraints,
        user_goal=user_goal,
        content=content_block,
    )
    return _llm_or_fallback(system, user, fallback=instructions.strip())


def auto_route(input_obj: Dict[str, Any], payload: Dict[str, Any]) -> Tuple[str, str]:
    """
    Router simple (if/else) para el modo 'auto'.

    Inputs esperados:
      - intent: str (ej: "explicar", "resumir", "reformular", "razonar")
      - topic: str (ej: "creditos", "mora", "desembolso", "cierre")
      - question/text: str
      - data/table/field opcional
    """
    intent = (input_obj.get("intent") or "").strip().lower()
    topic = (input_obj.get("topic") or "").strip().lower()
    question = (input_obj.get("question") or input_obj.get("text") or "").strip().lower()

    # Reglas
    if intent in {"explicar", "definir", "definicion"}:
        return "explain", explain(input_obj, payload)

    if intent in {"resumir", "resumen"}:
        return "summarize", summarize(input_obj, payload)

    if intent in {"reformular", "refrasear", "parafrasear"}:
        return "rephrase", rephrase(input_obj, payload)

    if intent in {"razonar", "justificar"}:
        return "reason", reason(input_obj, payload)

    # Señales en la pregunta
    if "qué es" in question or "que es" in question or "qué significa" in question or "que significa" in question:
        return "explain", explain(input_obj, payload)

    if any(w in question for w in ["resume", "resumen", "en pocas palabras"]):
        return "summarize", summarize(input_obj, payload)

    # Si viene data estructurada, normalmente es para resumen o explicación
    if input_obj.get("data") is not None and not intent:
        return "summarize", summarize(input_obj, payload)

    # Fallback
    return "reason", reason(input_obj, payload)


# ---- Prompting ----

def _build_prompt(
    task: str,
    audience: str,
    style: str,
    constraints: Dict[str, Any],
    user_goal: str,
    content: str,
) -> Tuple[str, str]:
    """
    Crea mensajes (system, user) para LLM.
    """
    length = (constraints.get("length") or "medium").lower()
    out_format = (constraints.get("format") or "paragraph").lower()

    audience_hint = {
        "analista": "El usuario es un analista financiero. Usa terminología técnica cuando sea útil.",
        "cliente": "El usuario es un cliente. Usa lenguaje claro, sin jerga innecesaria.",
    }.get(audience, "Ajusta el nivel de detalle al usuario.")

    style_hint = {
        "tecnico": "Tono técnico, preciso, orientado a definiciones y contexto.",
        "sencillo": "Tono sencillo y directo, con ejemplos si ayudan.",
        "ejecutivo": "Tono ejecutivo, breve, orientado a conclusiones y puntos clave.",
        "breve": "Sé breve y directo.",
    }.get(style, "Adapta el estilo según el contexto.")

    format_hint = "Responde en viñetas." if out_format == "bullets" else "Responde en párrafos claros."
    length_hint = {
        "short": "Máximo ~6-8 líneas.",
        "medium": "Longitud moderada.",
        "long": "Puedes extenderte si mejora la claridad.",
    }.get(length, "Longitud moderada.")

    system = "\n".join(
        [
            "Eres el Agente NLP del proyecto AIDA.",
            "Respondes SOLO en español.",
            "No inventes datos: si falta información, dilo y sugiere qué dato falta.",
            audience_hint,
            style_hint,
            format_hint,
            length_hint,
        ]
    )

    user = "\n".join(
        [
            f"Tarea: {task}",
            f"Objetivo: {user_goal}",
            "Contenido:",
            content,
        ]
    )

    return system, user


def _render_content_block(
    *,
    data: Any = None,
    text: str = "",
    concept: Optional[str] = None,
    table: Any = None,
    field: Any = None,
    context: Any = None,
) -> str:
    parts: List[str] = []

    if concept:
        parts.append(f"- Concepto/Topic: {concept}")

    if isinstance(text, str) and text.strip():
        parts.append(f"- Pregunta/Text:\n{text.strip()}")

    if context is not None:
        parts.append(f"- Contexto:\n{_safe_json(context)}")

    if table is not None:
        parts.append(f"- Tabla:\n{_safe_json(table)}")

    if field is not None:
        parts.append(f"- Campo:\n{_safe_json(field)}")

    if data is not None:
        parts.append(f"- Datos estructurados:\n{_safe_json(data)}")

    if not parts:
        return "(sin contenido)"
    return "\n".join(parts)


def _normalize_style(input_obj: Dict[str, Any], payload: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
    # audience: analista|cliente (default analista)
    audience = (input_obj.get("audience") or input_obj.get("user_type") or payload.get("audience") or "analista")
    audience = str(audience).strip().lower()

    # style: sencillo|tecnico|ejecutivo|breve (default ejecutivo para analista, sencillo para cliente)
    style = input_obj.get("style") or payload.get("style")
    if not style:
        style = "sencillo" if audience == "cliente" else "ejecutivo"
    style = str(style).strip().lower()

    constraints = input_obj.get("constraints") or payload.get("constraints") or {}
    if not isinstance(constraints, dict):
        constraints = {}

    return audience, style, constraints


# ---- LLM client (sin requests; solo stdlib) ----

def _llm_or_fallback(system: str, user: str, fallback: str) -> str:
    provider = DEFAULT_PROVIDER.strip().lower()

    # Forzar mock si no hay red o para tests:
    if provider == "mock" or os.getenv("NLP_FORCE_MOCK", "").lower() in {"1", "true", "yes"}:
        return fallback

    if provider == "ollama":
        try:
            return _call_ollama_chat(system, user)
        except Exception:
            return fallback

    # Provider desconocido: fallback
    return fallback


def _post_json(url: str, payload: Dict[str, Any], timeout_s: float) -> Dict[str, Any]:
    """
    POST JSON usando urllib (stdlib).
    Devuelve dict parseado desde JSON.
    Lanza RuntimeError con detalle en errores HTTP/conexión.
    """
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return json.loads(raw) if raw else {}
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Invalid JSON response: {e}") from e

    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", errors="replace")
        except Exception:
            detail = ""
        raise RuntimeError(f"HTTP {e.code} calling {url}: {detail}") from e

    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection error calling {url}: {e}") from e


def _call_ollama_chat(system: str, user: str) -> str:
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": DEFAULT_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }

    data = _post_json(url, payload, timeout_s=REQUEST_TIMEOUT_S)

    # Respuesta típica: {"message": {"role":"assistant", "content":"..."}, ...}
    msg = (data or {}).get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Empty response from Ollama.")
    return content.strip()


# ---- Fallbacks (deterministas, sin LLM) ----

def _fallback_summarize(*, data: Any, text: str, audience: str, style: str) -> str:
    if data is not None:
        return (
            f"Resumen ({style}, {audience}): se recibieron datos estructurados con "
            f"{_count_items(data)} elementos/claves relevantes."
        )
    t = (text or "").strip()
    if len(t) <= 220:
        return t
    return t[:220].rstrip() + "…"


def _fallback_explain(*, concept: Any, question: str, table: Any, field: Any, audience: str, style: str) -> str:
    if isinstance(concept, str) and concept.strip():
        c = concept.strip().lower()
        glossary = {
            "días de mora": "Los días de mora son la cantidad de días que un pago se encuentra atrasado respecto a su fecha de vencimiento.",
            "dias de mora": "Los días de mora son la cantidad de días que un pago se encuentra atrasado respecto a su fecha de vencimiento.",
            "saldo vencido": "El saldo vencido es la parte del saldo del crédito que está vencida (pagos que debieron realizarse y no se pagaron a tiempo).",
            "reprogramación de crédito": "Una reprogramación de crédito es un cambio pactado en el calendario de pagos (fechas/plazo/cuota) para adecuarlo a la capacidad de pago.",
            "reprogramacion de credito": "Una reprogramación de crédito es un cambio pactado en el calendario de pagos (fechas/plazo/cuota) para adecuarlo a la capacidad de pago.",
            "condonación": "Una condonación es la eliminación total o parcial de una deuda (o de intereses/moras) según condiciones definidas por la entidad.",
            "condonacion": "Una condonación es la eliminación total o parcial de una deuda (o de intereses/moras) según condiciones definidas por la entidad.",
        }
        if c in glossary:
            return glossary[c]

    if table is not None:
        if isinstance(table, dict):
            name = str(table.get("name") or table.get("table") or "").strip()
            desc = str(table.get("description") or "").strip()
            if desc:
                return f"La tabla {name or '(sin nombre)'} almacena: {desc}"
        return "Puedo explicar la tabla si me indicas su nombre y (si es posible) una breve descripción o sus campos principales."

    if field is not None:
        if isinstance(field, dict):
            n = field.get("name")
            d = field.get("description")
            t = field.get("table")
            base = f"El campo {n} "
            if t:
                base += f"de la tabla {t} "
            if d:
                base += f"representa: {d}"
            else:
                base += "representa un atributo de negocio (falta la descripción)."
            return base
        return "Puedo explicar el campo si me indicas su nombre, tabla y descripción."

    q = (question or "").strip()
    if q:
        return f"Para responder con precisión necesito más contexto sobre: {q}"
    return "Necesito más información para explicar lo solicitado."


def _fallback_reason(*, question: str) -> str:
    q = question.strip()
    return f"Para responder '{q}', necesito los datos o el contexto específico (por ejemplo: cuenta, periodo, producto)."


def _count_items(obj: Any) -> int:
    if isinstance(obj, dict):
        return len(obj)
    if isinstance(obj, list):
        return len(obj)
    return 1


# ---- Response helpers ----

def _ok(*, task: str, answer: str, language: str, t0: float) -> Dict[str, Any]:
    return {
        "ok": True,
        "task": task,
        "language": language,
        "answer": answer,
        "meta": {
            "latency_ms": int((time.time() - t0) * 1000),
            "provider": DEFAULT_PROVIDER,
            "model": DEFAULT_MODEL,
        },
    }


def _error(message: str, *, task: Optional[str], t0: float) -> Dict[str, Any]:
    return {
        "ok": False,
        "task": task,
        "language": "es",
        "error": message,
        "meta": {
            "latency_ms": int((time.time() - t0) * 1000),
            "provider": DEFAULT_PROVIDER,
            "model": DEFAULT_MODEL,
        },
    }


def _safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    except Exception:
        return str(obj)
