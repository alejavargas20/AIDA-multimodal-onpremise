# agents/data/action_classifier/predict.py
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from pathlib import Path
from typing import Dict, Any, List, Tuple


class ActionClassifier:
    def __init__(self, model_dir: str):
        p = Path(model_dir)
        if not p.exists():
            raise FileNotFoundError(f"No existe model_dir: {model_dir}")

        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        self.model.eval()

    def predict(self, text: str, top_k: int = 5) -> Dict[str, Any]:
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True)
        with torch.no_grad():
            out = self.model(**inputs)
            probs = torch.softmax(out.logits, dim=-1).squeeze(0)

        top_k = min(top_k, probs.shape[0])
        vals, idxs = torch.topk(probs, k=top_k)

        top = []
        for score, idx in zip(vals.tolist(), idxs.tolist()):
            label = self.model.config.id2label[int(idx)]
            top.append({"action": label, "score": float(score)})

        return {"top1": top[0], "topk": top}
