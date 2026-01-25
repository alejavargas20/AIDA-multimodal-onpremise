from __future__ import annotations

import os
from typing import Any, Dict, List


def transcribe_audio(
    *,
    file_path: str,
    language: str = "es",
    model: str = "base",
    provider: str = "whisper",
) -> Dict[str, Any]:
    """
    STT: audio -> texto.

    provider:
      - whisper: openai-whisper (requiere ffmpeg instalado en el sistema)
      - mock: devuelve texto dummy (para tests)
    """
    provider = (provider or "whisper").strip().lower()

    if provider == "mock" or os.getenv("VOICE_FORCE_MOCK", "").lower() in {"1", "true", "yes"}:
        return {
            "text": "(mock) Transcripción simulada.",
            "segments": [],
            "language": language,
            "provider": "mock",
            "model": model,
        }

    if provider != "whisper":
        raise RuntimeError(f"Unsupported STT provider: {provider}")

    try:
        import whisper  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "STT provider 'whisper' no disponible. Instala dependencias: pip install -U openai-whisper"
        ) from e

    stt_model = whisper.load_model(model)
    result = stt_model.transcribe(file_path, language=language, task="transcribe")

    text = (result or {}).get("text") or ""
    segments = (result or {}).get("segments") or []
    safe_segments: List[Dict[str, Any]] = []

    for s in segments:
        if isinstance(s, dict):
            safe_segments.append(
                {
                    "start": s.get("start"),
                    "end": s.get("end"),
                    "text": s.get("text"),
                }
            )

    return {
        "text": text.strip(),
        "segments": safe_segments,
        "language": language,
        "provider": "whisper",
        "model": model,
    }
