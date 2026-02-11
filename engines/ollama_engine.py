"""
Módulo para interactuar con Ollama.
"""

import ollama
from typing import Dict, Any

def call_ollama(model: str, prompt: str) -> Dict[str, Any]:
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response