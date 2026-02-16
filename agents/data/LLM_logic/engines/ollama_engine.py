# agents/data/LLM_logic/engines/ollama_engine.py

from __future__ import annotations
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
import time
import ollama


def _now() -> str:
    return time.strftime("%H:%M:%S")


def call_ollama(
    model: str,
    prompt: str,
    *,
    timeout_seconds: int = 180,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Llamada robusta a Ollama con timeout duro.

    - timeout_seconds: aumenta para evitar fallos por cold start.
    - options: controla velocidad/longitud y reduce “explicaciones”.
    """
    if options is None:
        options = {}

    # Defaults razonables para SQL
    options.setdefault("temperature", 0)
    options.setdefault("num_predict", 256)   # limita tokens => responde más rápido
    options.setdefault("top_p", 0.9)

    # Cortar si intenta meter markdown o explicar
    # (no es perfecto, pero reduce mucho esos casos)
    options.setdefault("stop", ["```", "Para ", "En este", "Explicación", "Explanation:"])

    print(f"[{_now()}][OLLAMA] model={model} prompt_chars={len(prompt)} timeout={timeout_seconds}s", flush=True)

    def _run() -> Dict[str, Any]:
        return ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options=options,
        )

    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(_run)
        try:
            out = fut.result(timeout=timeout_seconds)
            print(f"[{_now()}][OLLAMA] ok", flush=True)
            return out
        except FuturesTimeout:
            print(f"[{_now()}][OLLAMA] TIMEOUT after {timeout_seconds}s", flush=True)
            raise TimeoutError(f"Ollama timeout after {timeout_seconds}s")
