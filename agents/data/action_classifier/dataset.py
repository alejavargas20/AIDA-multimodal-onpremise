# agents/data/action_classifier/dataset.py
import json
from pathlib import Path
from typing import List, Dict, Tuple


def load_action_dataset(json_path: str) -> Tuple[List[str], List[str]]:
    """
    Devuelve: texts, labels (str)
    Espera formato:
    {
      "meta": {...},
      "data": [{"text": "...", "label": "action_1"}, ...]
    }
    """
    p = Path(json_path)
    if not p.exists():
        raise FileNotFoundError(f"No existe el dataset: {json_path}")

    obj = json.loads(p.read_text(encoding="utf-8"))
    rows = obj.get("data", [])
    if not rows:
        raise ValueError("El dataset no tiene 'data' o está vacío.")

    texts, labels = [], []
    for r in rows:
        t = (r.get("text") or "").strip()
        lab = (r.get("label") or "").strip()
        if not t or not lab:
            continue
        texts.append(t)
        labels.append(lab)

    if not texts:
        raise ValueError("No se encontraron ejemplos válidos (text/label).")

    return texts, labels
