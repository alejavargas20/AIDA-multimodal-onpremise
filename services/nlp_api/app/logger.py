import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List


LOG_DIR = os.getenv("LOG_DIR", "data/logs")
LOG_FILE = os.getenv("LOG_FILE", os.path.join(LOG_DIR, "nlp_requests.jsonl"))


def _ensure_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def _truncate(s: str, n: int = 400) -> str:
    s = s or ""
    return s if len(s) <= n else s[:n] + "…"


def _safe_used_docs(used_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    safe = []
    for d in used_docs or []:
        safe.append(
            {
                "source": d.get("source"),
                "page": d.get("page"),
                "snippet": _truncate(d.get("snippet", ""), 250),
            }
        )
    return safe


def append_log(payload: Dict[str, Any]) -> None:
    """
    Guarda 1 evento en JSONL. (anonimizable: aquí ya truncamos snippets)
    """
    _ensure_dir()
    payload = dict(payload)
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()

    if "used_docs" in payload:
        payload["used_docs"] = _safe_used_docs(payload["used_docs"])

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
