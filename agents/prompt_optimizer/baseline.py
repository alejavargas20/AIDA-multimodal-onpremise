# aida-multimodal-onpremise/agents/prompt_optimizer/baseline.py

from __future__ import annotations
from typing import Dict, Tuple

# Definimos palabras clave que indican claramente una intención de cálculo o consulta de datos
DATA_TRIGGERS = [
    "cuanto", "cuantos", "cuántos", "cuántas", "cantidad",
    "monto", "total", "suma",
    "promedio", "media",
    "porcentaje", "%", "tasa",
    "plazo", "fecha", "vence", "vencimiento",
    "distribuye", "concentra", "comportamiento",
    "saldo", "deuda", "cuota", "pagar",
    "estado", "vigente", "atraso", "días de mora",
    "reprogramadas", "condonación", "castigado",
    "cosecha", "cartera", "sow",
    "mi crédito", "mi saldo", "mi desembolso" # Personalización cliente
]

# Definimos palabras clave que indican claramente una pregunta conceptual - NLP
CONCEPT_TRIGGERS = [
    "que es", "qué es", "que son", "qué son", "que significa", "qué significa",
    "como funciona", "cómo funciona", "definicion", "concepto",
    "afecta", "pasa si", "por qué", "por que",
    "diferencia", "explícame"
]

# INTENT_KEYWORDS = {
#     "procesar_documento": ["documento", "pdf", "imagen", "ocr", "archivo", "adjunto"],
#     "resumen": ["resume", "resumen", "resúmeme", "sintetiza", "síntesis"],
#     "analisis_financiero": ["riesgo", "mora", "cartera", "saldo", "impago", "evolución", "default"],
#     "perfil_cliente": ["perfil", "segmento", "cliente", "comportamiento", "caracteriza"],
#     "alerta_riesgo": ["alerta", "riesgo alto", "detección", "anomalía"],
#     "consulta_datos": ["consulta", "datos", "kpi", "métrica", "estadística"],
# }

SUMMARIZE_TRIGGERS = ["resume", "resumen", "resumeme", "sintetiza", "sintesis"]
REPHRASE_TRIGGERS = ["reescribe", "reformula", "parafrasea", "cambia el tono", "rephrase"]

# Mapeo de intenciones basado en el contexto del negocio
INTENT_DEFINITIONS = {
    # 1. Consultas Analíticas (Analista) - Agregaciones y Métricas
    "analitica_desembolsos": ["desembols", "colocacion", "clientes nuevos", "region", "oficina", "producto"],
    "analitica_sistema": ["sistema financiero", "sfn", "mercado", "castigado", "sow", "microempresa", "tramos"],
    "analitica_cartera": ["cartera", "clientes unicos", "mora", "vencido", "reprogram", "condonacion", "cosecha"],
    
    # 2. Consultas Personales (Cliente) - Datos específicos
    "info_cliente": ["mi crédito", "mi credito", "mi saldo", "mi cuota", "mi desembolso", "vence", "pagar", "atraso", "vigente"],

    # 3. Educación Financiera (NLP) - Definiciones
    "educacion_financiera": ["que es", "significa", "concepto", "afecta", "pasa si", "definicion"],
    
    # 4. DOCUMENTOS
    "procesar_documento": ["documento", "pdf", "imagen", "archivo", "adjunto", "foto", "lee esto"]
}


def baseline_intent(text: str) -> Tuple[str, float]:
    """
    Clasifica la intención del usuario usando reglas simples basadas en palabras clave.
    Devuelve una tupla (intent, confidence).
    """
    t = (text or "").lower()

    # 1. ¿Pide resumir?
    if any(trigger in t for trigger in SUMMARIZE_TRIGGERS):
        return "resumen", 0.95

    # 2. ¿Pide reformular?
    if any(trigger in t for trigger in REPHRASE_TRIGGERS):
        return "reformulacion", 0.95
        
    # 3. ¿Es una pregunta conceptual?
    if any(trigger in t for trigger in CONCEPT_TRIGGERS):
        return "educacion_financiera", 0.95
    
    # 4. ¿Pide un cálculo o dato?
    is_data_request = any(trigger in t for trigger in DATA_TRIGGERS)

    best_intent = "otro_ayuda"
    best_score = 0
    
    for intent, kws in INTENT_DEFINITIONS.items():
        score = sum(1 for kw in kws if kw in t)
        # Si pide datos y coincide con el tema, aumentamos relevancia
        if is_data_request and intent != "educacion_financiera":
            score += 2
        if score > best_score:
            best_score = score
            best_intent = intent

    conf = min(0.4 + 0.15 * best_score, 0.95) if best_score > 0 else 0.3

    # Fallback: Si pide datos pero no sabemos de qué tema
    if best_intent == "otro_ayuda" and is_data_request:
        return "analitica_general", 0.7
    
    return best_intent, conf


def baseline_action_stub(intent: str) -> Dict[str, str]:
# # Actions aligned with Desarrollo: action is verb-only; orchestrator builds tool_name as "<agent>.<action>"
#     if intent in ("analisis_financiero", "consulta_datos", "perfil_cliente", "alerta_riesgo"):
#         return {"agent": "data", "action": "fetch_metrics"}
#     if intent in ("resumen",):
#         return {"agent": "nlp", "action": "summarize"}
#     if intent in ("procesar_documento",):
#         return {"agent": "image", "action": "normalized_text"}
#     return {"agent": "nlp", "action": "reason"}

    """
    Define el Agente y la Acción por defecto según el intent.
    """
    # Grupo DATOS
    if intent in ("analitica_desembolsos", "analitica_sistema", "analitica_cartera", "info_cliente", "analitica_general"):
        return {"agent": "data", "action": "fetch_metrics"}

    # GRUPO NLP
    if intent == "resumen":
        return {"agent": "nlp", "action": "summarize"}
    
    if intent == "reformulacion":
        return {"agent": "nlp", "action": "rephrase"}

    if intent == "educacion_financiera":
        return {"agent": "nlp", "action": "explain"}
    
    if intent == "procesar_documento": 
        return {"agent": "nlp", "action": "reason"}

    # DEFAULT
    return {"agent": "nlp", "action": "reason"}
