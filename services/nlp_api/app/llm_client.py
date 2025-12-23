from dotenv import load_dotenv
load_dotenv()
import os
from typing import List, Dict, Any
import requests

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

MODEL_NAME = os.getenv("MODEL_NAME") or os.getenv("OLLAMA_MODEL", "llama3.2:3b")


def chat_ollama(messages: List[Dict[str, Any]], temperature: float = 0.2, timeout: int = 180) -> str:
    """
    messages: [{"role":"system|user|assistant", "content":"..."}]
    Devuelve: string con la respuesta del modelo
    """
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }

    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    return data["message"]["content"]


