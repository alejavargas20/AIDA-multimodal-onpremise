# agents/data/action_classifier/utils.py
from typing import Dict, Any, Optional
from agents.data.action_classifier.labels import label2id


def build_classifier_text(
    payload: Dict[str, Any],
    hints: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Construye el texto de entrada al clasificador.
    Recomendado: normalized + optimized.
    hints es opcional (ej. {"period":"ultimo_mes","scope":"cliente"}).
    """

    normalized_text = (payload.get("normalized_text") or "").strip()
    optimized_prompt = (payload.get("optimized_prompt") or "").strip()

    parts = []
    if normalized_text:
        parts.append(f"NORMALIZED: {normalized_text}")
    if optimized_prompt:
        parts.append(f"OPTIMIZED: {optimized_prompt}")

    if hints:
        # convertimos hints a texto controlado
        kv = "; ".join([f"{k}={v}" for k, v in hints.items()])
        parts.append(f"HINTS: {kv}")

    return "\n".join(parts).strip()


def validate_label(label: str) -> None:
    """
    Lanza error si el label no existe en nuestro espacio de acciones.
    """
    if label not in label2id:
        raise ValueError(f"Label '{label}' no está en LABELS. Revisa el dataset.")
