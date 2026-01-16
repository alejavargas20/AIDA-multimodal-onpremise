# agents/data/action_classifier/labels.py
import json
from pathlib import Path
from typing import Dict, List, Tuple


def load_labels_from_dataset(
    dataset_path: str,
) -> Tuple[List[str], Dict[str, int], Dict[int, str]]:
    """
    Lee action_training_dataset.json y devuelve:
    - labels ordenados: ["action_1", ...]
    - label2id
    - id2label
    """
    p = Path(dataset_path)
    print(p)
    if not p.exists():
        raise FileNotFoundError(f"No existe dataset: {dataset_path}")

    obj = json.loads(p.read_text(encoding="utf-8"))
    rows = obj.get("data", [])
    if not rows:
        raise ValueError("El dataset no tiene 'data' o está vacío.")

    labels = sorted(
        list({r["label"] for r in rows if "label" in r}),
        key=lambda x: int(x.split("_")[1]),
    )

    label2id = {lab: i for i, lab in enumerate(labels)}
    id2label = {i: lab for lab, i in label2id.items()}
    return labels, label2id, id2label


# labels, label2id, id2label = load_labels_from_dataset(
#     "agents/data/catalog/action_training_dataset.json"
# )

# print(labels, label2id, id2label)
