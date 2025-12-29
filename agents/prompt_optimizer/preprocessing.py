from __future__ import annotations

import re
from typing import Any, Dict


RE_AMOUNT = re.compile(r"(\d+[.,]?\d*)\s?(€|eur|euros)?", re.IGNORECASE)
RE_PERCENT = re.compile(r"(\d+[.,]?\d*)\s?%", re.IGNORECASE)
RE_DATE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")


def normalize_text(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def detect_language_simple(text: str) -> str:
    # Minimal heuristic; can be replaced later
    if any(w in (text or "").lower() for w in ["qué", "cómo", "hacer", "dame", "resumen"]):
        return "es"
    return "unknown"


def extract_entities(text: str) -> Dict[str, Any]:
    amounts = [m.group(0) for m in RE_AMOUNT.finditer(text or "")]
    percents = [m.group(0) for m in RE_PERCENT.finditer(text or "")]
    dates = [m.group(0) for m in RE_DATE.finditer(text or "")]
    return {
        "amounts": amounts[:5],
        "percents": percents[:5],
        "dates": dates[:5],
    }


def preprocess(payload: Dict[str, Any]) -> Dict[str, Any]:
    user_text = normalize_text(payload.get("user_text", ""))
    lang = payload.get("metadata", {}).get("language") or detect_language_simple(user_text)
    input_source = payload.get("metadata", {}).get("input_source", "unknown")

    entities = extract_entities(user_text)

    return {
        "user_text": user_text,
        "language": lang,
        "input_source": input_source,
        "entities": entities,
        "history": payload.get("history", []),
        "constraints": payload.get("constraints", {}),
    }
