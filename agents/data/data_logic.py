# agents/data/data_logic.py
from typing import Dict, Any
from agents.data.action_classifier.predict import ActionClassifier
from agents.data.action_classifier.utils import build_classifier_text

MODEL_DIR = "agents/data/action_classifier/artifacts/roberta_bne_action"

_classifier = None


def process(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload esperado (del orquestador):
      - normalized_text (str)
      - optimized_prompt (str)
      - intent_json (dict) opcional
    """
    global _classifier
    if _classifier is None:
        _classifier = ActionClassifier(MODEL_DIR)

    # input para clasificar (recomendado: raw + optimized)
    text_for_cls = build_classifier_text(payload)

    pred = _classifier.predict(text_for_cls, top_k=5)

    return {
        "status": "ok",
        "predicted_action": pred["top1"]["action"],
        "score": pred["top1"]["score"],
        "topk": pred["topk"],
    }
