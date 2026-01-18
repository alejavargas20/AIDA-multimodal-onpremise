from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, List, Optional


class LLMClientError(RuntimeError):
    pass


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v.strip() if v and v.strip() else default


def call_llm_chat(messages: List[Dict[str, str]]) -> str:
    """
    Calls a local LLM server via HTTP (default: Ollama /api/chat).
    Returns raw text produced by the model (expected: JSON-only).
    """
    base_url = _env("LLM_BASE_URL", "http://localhost:11434")
    endpoint = _env("LLM_CHAT_ENDPOINT", "/api/chat")
    model = _env("LLM_MODEL", "llama3")

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        # Keep deterministic-ish for JSON planning
        "options": {
            "temperature": float(_env("LLM_TEMPERATURE", "0.1")),
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=f"{base_url}{endpoint}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    timeout_s = float(_env("LLM_TIMEOUT_SECONDS", "30"))

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise LLMClientError(f"LLM server call failed: {exc}") from exc

    # Ollama /api/chat response typically:
    # { "message": { "content": "..." }, ... }
    try:
        obj = json.loads(raw)
        content = obj.get("message", {}).get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception:
        # If not JSON, just return raw
        pass

    return raw.strip()
