from __future__ import annotations

from typing import Dict, Tuple


INTENT_KEYWORDS = {
    "procesar_documento": ["documento", "pdf", "imagen", "ocr", "archivo", "adjunto"],
    "resumen": ["resume", "resumen", "resúmeme", "sintetiza", "síntesis"],
    "analisis_financiero": ["riesgo", "mora", "cartera", "saldo", "impago", "evolución", "default"],
    "perfil_cliente": ["perfil", "segmento", "cliente", "comportamiento", "caracteriza"],
    "alerta_riesgo": ["alerta", "riesgo alto", "detección", "anomalía"],
    "consulta_datos": ["consulta", "datos", "kpi", "métrica", "estadística"],
}


def baseline_intent(text: str) -> Tuple[str, float]:
    t = (text or "").lower()

    best_intent = "otro_ayuda"
    best_score = 0

    for intent, kws in INTENT_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in t)
        if score > best_score:
            best_score = score
            best_intent = intent

    # Normalize confidence roughly
    conf = min(0.2 + 0.15 * best_score, 0.85) if best_score > 0 else 0.4
    return best_intent, conf


def baseline_action_stub(intent: str) -> Dict[str, str]:
# Actions aligned with Desarrollo: action is verb-only; orchestrator builds tool_name as "<agent>.<action>"
    if intent in ("analisis_financiero", "consulta_datos", "perfil_cliente", "alerta_riesgo"):
        return {"agent": "data", "action": "fetch_metrics"}
    if intent in ("resumen",):
        return {"agent": "nlp", "action": "summarize"}
    if intent in ("procesar_documento",):
        return {"agent": "image", "action": "extract_text"}
    return {"agent": "nlp", "action": "answer"}
