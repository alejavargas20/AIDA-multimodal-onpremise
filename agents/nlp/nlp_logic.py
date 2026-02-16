# aida-multimodal-onpremise/agents/nlp/nlp_logic.py

"""
Agente NLP ¡

Este módulo implementa UNA única función pública para ser llamada desde el MCP:
    from agents.nlp.nlp_logic import process
    process(payload: dict) -> dict

El orquestador decide qué hacer y envía en `payload["task"]` la acción a ejecutar.
"""

from __future__ import annotations

import os
import sys
import time
import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional, Tuple, List


# # ---- Config (env) ----
# DEFAULT_MODEL = os.getenv("NLP_MODEL", "llama3.2:3b")
# DEFAULT_PROVIDER = os.getenv("NLP_PROVIDER", "ollama")  # "ollama" | "mock"
# OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# REQUEST_TIMEOUT_S = float(os.getenv("NLP_REQUEST_TIMEOUT_S", "30"))
# --- ENCABEZADO DEL ARCHIVO: Agregar import ---

# ---- Config (Actualizada para Motor Híbrido) ----
DEFAULT_MODEL = "Llama-3.1-8B-Hybrid"
DEFAULT_PROVIDER = "Local-RTX5090/CPU"

# Asegurar path para encontrar el engine
current = os.path.dirname(os.path.abspath(__file__))
parent = os.path.dirname(current)
if parent not in sys.path:
    sys.path.append(parent)

# Importar el motor híbrido
try:
    from local_engine import generate_response
except ImportError:
    # Fallback por si acaso no encuentra el archivo, para no romper el import
    print("ERROR: No se pudo importar local_engine. Verifica la ruta.")
    def generate_response(msgs): return "Error crítico: Motor no encontrado."


# ---- Public API ----
SUPPORTED_TASKS = {
    "summarize",
    "explain",
    "rephrase",
    "reason",
    "generate",
}


def process(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Punto de entrada del Agente NLP.

    Payload esperado (mínimo):
    {
      "task": "summarize|explain|rephrase|reason|generate",
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

    # Dispatch a la función específica
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
        else:
            return _error("Task router reached unexpected state.", task=task, t0=t0)

        return _ok(task=task, answer=answer, language=language, t0=t0)

    except Exception as e:
        print(f"[NLP Agent] Error processing task '{task}': {e}")
        return _error(f"Unhandled error: {type(e).__name__}: {e}", task=task, t0=t0)


# ---- Internal task handlers ----

def summarize(input_obj: Dict[str, Any], payload: Dict[str, Any]) -> str:
    """
    Resume datos estructurados (p. ej. salida del Agente de Datos) o texto largo.
    Inputs posibles:
      - data: dict|list (preferido)
      - text: str (alternativo)
      - audience: "analista"|"cliente"
      - style: "ejecutivo"|"tecnico"|"sencillo"
      - constraints: {"length": "short|medium|long", "format": "bullets|paragraph"}

    Instrucciones:
    - Extrae los puntos más relevantes.
    - Si hay métricas, menciona solo las más importantes.
    - Usa lenguaje ejecutivo para analistas.
    - Usa lenguaje sencillo para clientes.
    - No más de 5 a 7 líneas salvo que se indique lo contrario.

    """
    audience, style, constraints = _normalize_style(input_obj, payload)

    data = input_obj.get("data")
    text = input_obj.get("text") or input_obj.get("question") or ""

    if data is None and (not isinstance(text, str) or not text.strip()):
        raise ValueError("summarize requires 'input.data' or non-empty 'input.text'.")

    user_goal = input_obj.get("goal") or "Resume la información principal."
    content_block = _render_content_block(data=data, text=text)

    specific_instructions = """
    Tu tarea es generar un RESUMEN EJECUTIVO de información financiera.
    Instrucciones:
    - Analiza el contenido y extrae los puntos más críticos (saldos totales, variaciones de mora, montos de desembolso).
    - Si el contenido tiene métricas, prioriza las que presenten desviaciones o alertas.
    - Estilo para ANALISTAS: Lenguaje técnico, preciso y enfocado en KPIs.
    - Estilo para CLIENTES: Lenguaje sencillo, empático y explicativo.
    - RESTRICCIÓN: No excedas las 5 a 7 líneas de texto.
    - FORMATO: Usa viñetas para datos numéricos y un párrafo corto para la conclusión principal.
    """

    system, user = _build_prompt(
        task="summarize",
        audience=audience,
        specific_instructions=specific_instructions,
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
    Tu tarea es EXPLICAR un concepto financiero o el significado de datos.
    Instrucciones:
    - Define el concepto con claridad.
    - Usa ejemplos si ayudan.
    - Si el concepto proviene de un documento o cálculo, explica qué significa para el usuario.
    - No uses jerga innecesaria con clientes.
    Ejemplos de conceptos:
    - días de mora
    - saldo vencido
    - reprogramación
    - condonación
    - cartera castigada

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

    specific_instructions = """
    Tu tarea es EXPLICAR conceptos financieros o el significado de datos específicos del negocio.
    Instrucciones:
    - Define el concepto solicitado con total claridad y rigor técnico.
    - Usa ejemplos prácticos del entorno bancario si ayudan a la comprensión.
    - Si el concepto proviene de un cálculo o dato estructurado, explica qué impacto tiene esa cifra para el usuario.
    - Evita jerga técnica compleja si la audiencia es un "Cliente".
    - Conceptos clave de dominio: Días de mora (atraso), Saldo vencido, Reprogramación (ajuste de cuotas), Condonación (perdón de deuda), Cartera Castigada.
    """

    system, user = _build_prompt(
        task="explain",
        audience=audience,
        specific_instructions=specific_instructions,
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

    specific_instructions = """
    Tu tarea es REFORMULAR el texto proporcionado para mejorar su impacto y claridad.
    Instrucciones:
    - Ajusta el vocabulario y la estructura gramatical según la audiencia (Analista o Cliente).
    - Mantén el significado original de forma íntegra.
    - Si el texto original es muy técnico y la audiencia es un "Cliente", simplifícalo sin perder precisión.
    - Si el texto es plano y la audiencia es un "Analista", dale un tono más corporativo y ejecutivo.
    """

    system, user = _build_prompt(
        task="rephrase",
        audience=audience,
        specific_instructions=specific_instructions,
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

    specific_instructions = """
    Tu tarea es RAZONAR y JUSTIFICAR comportamientos financieros basándote en la evidencia.
    Instrucciones:
    - Responde a preguntas complejas de tipo "¿Por qué?", "¿A qué se debe?" o "¿Qué impacto tiene?".
    - Relaciona causas y efectos de forma lógica (ej: Relación entre el aumento del plazo y el incremento del riesgo).
    - Identifica tendencias en los datos estructurados y formula hipótesis basadas únicamente en ellos.
    - ADVERTENCIA DE RIESGO: Si detectas indicadores de peligro financiero (ej: mora creciente), menciónalo con cautela y profesionalismo.
    - Si faltan datos para llegar a una conclusión definitiva, dilo explícitamente.
    """

    system, user = _build_prompt(
        task="reason",
        audience=audience,
        specific_instructions=specific_instructions,
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

    specific_instructions = """
    Tu tarea es GENERAR contenido financiero nuevo basado en las instrucciones proporcionadas.
    Instrucciones:
    - Crea informes, correos de notificación, alertas de riesgo o recomendaciones de pago.
    - Estructura el contenido con encabezados claros si la extensión lo requiere.
    - Sigue fielmente los DATOS ESTRUCTURADOS si se proporcionan. NO inventes cifras ni asumas valores que no estén en los datos.
    - Oculta la complejidad técnica: No menciones palabras como "JSON", "Base de datos", "SQL" o "Query". Presenta los números de forma amigable.
    - Si hablas con un "Cliente", usa un tono empático, transparente y resolutivo. Si hablas con un "Analista", ve directo al grano.
    """

    system, user = _build_prompt(
        task="generate",
        audience=audience,
        specific_instructions=specific_instructions,
        style=style,
        constraints=constraints,
        user_goal=user_goal,
        content=content_block,
    )
    return _llm_or_fallback(system, user, fallback=instructions.strip())


# ---- Prompting ----

def _llm_or_fallback(system: str, user: str, fallback: str) -> str:
    """
    Llama al Motor Híbrido Local.
    """
    try:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
        # Llamada directa al engine local
        return generate_response(messages)
    except Exception as e:
        print(f"[NLP Agent] Error en inferencia local: {e}")
        return fallback

def _build_prompt(
    task: str,
    audience: str,
    specific_instructions: str,
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

    # --- 2. SYSTEM PROMPT (Identidad + Reglas + Tus Hints) ---
    system = f"""
    Eres el Agente NLP del sistema AIDA, un asistente experto en análisis financiero senior. 
    Respondes SIEMPRE en español claro y profesional.

    REGLAS DE ORO:
    - NO inventes datos ni menciones nombres de tablas SQL o lenguaje interno de BD.
    - Si los datos son insuficientes, indícalo claramente.
    - Prioriza precisión numérica y utilidad.

    CONFIGURACIÓN DE LA RESPUESTA:
    - Audiencia: {audience_hint}
    - Estilo: {style_hint}
    - Formato: {format_hint}
    - {length_hint}

    INSTRUCCIONES ESPECÍFICAS DE LA TAREA:
    {specific_instructions}
    """.strip()

    # User Prompt: Estructura de la petición actual
    user = f"""
    TAREA A REALIZAR: {task.upper()}
    AUDIENCIA OBJETIVO: {audience.capitalize()}
    OBJETIVO DEL USUARIO (user_goal): {user_goal}

    CONTENIDO DE ENTRADA (DATOS/TEXTO):
    {content}

    Por favor, genera la respuesta siguiendo estrictamente las reglas del Sistema y el objetivo del usuario.
    Respuesta:
    """
    
    return system.strip(), user.strip()


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
    # 1. Prioridad 1: Rol del metadato (Login)
    # 2. Prioridad 2: Rol definido en la tarea
    # 3. Default: cliente (por seguridad financiera)
    metadata = payload.get("metadata", {})

    raw_audience = (
        metadata.get("user_role") or 
        input_obj.get("audience") or 
        payload.get("audience") or 
        "cliente"
    )

    audience = str(raw_audience).strip().lower()

    if audience not in ["analista", "cliente"]:
            audience = "cliente"

    # style: sencillo|tecnico|ejecutivo|breve (default ejecutivo para analista, sencillo para cliente)
    style = input_obj.get("style") or payload.get("style")
    if not style:
        style = "sencillo" if audience == "cliente" else "ejecutivo"
    style = str(style).strip().lower()

    constraints = input_obj.get("constraints") or payload.get("constraints") or {}
    if not isinstance(constraints, dict):
        constraints = {}

    return audience, style, constraints


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

