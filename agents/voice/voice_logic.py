from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from .engines.stt_engine import transcribe_audio
from .engines.tts_engine import synthesize_speech


SUPPORTED_ACTIONS = {"transcribe", "synthesize"}  # STT | TTS


def process(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agente de Voz (STT/TTS) para AIDA.

    Entrada única (MCP):
        from agents.voice.voice_logic import process
        process(payload: dict) -> dict

    Acciones:
      - transcribe: audio -> texto (Whisper o mock)
      - synthesize: texto -> audio (Coqui / pyttsx3 / mock)

    Payload STT:
      {
        "action": "transcribe",   # o "task"
        "file_path": "/path/audio.wav",
        "config": {
          "language": "es",
          "provider": "whisper|mock" (opcional),
          "model": "base|small|medium|large" (opcional)
        }
      }

    Payload TTS:
      {
        "action": "synthesize",
        "text": "Hola...",
        "output_path": "/path/out.wav" (opcional),
        "config": {
          "provider": "coqui|pyttsx3|mock" (opcional),
          "model_name": "..." (opcional),
          "speaker_wav": "/path/voice.wav" (opcional)
        }
      }
    """
    t0 = time.time()

    if not isinstance(payload, dict):
        return _error("Payload must be a dict.", action=None, t0=t0)

    action = payload.get("action") or payload.get("task")  # compat
    if not action or not isinstance(action, str):
        return _error("Missing 'action' (or 'task') in payload.", action=None, t0=t0)

    action = action.strip().lower()
    if action not in SUPPORTED_ACTIONS:
        return _error(
            f"Unsupported voice action: {action}. Supported: {sorted(SUPPORTED_ACTIONS)}",
            action=action,
            t0=t0,
        )

    config = payload.get("config") or {}
    if not isinstance(config, dict):
        config = {}

    try:
        if action == "transcribe":
            file_path = payload.get("file_path")
            if not file_path or not isinstance(file_path, str):
                return _error("Missing 'file_path' for transcribe.", action=action, t0=t0)

            language = str(config.get("language") or os.getenv("VOICE_LANGUAGE", "es")).strip().lower()
            model = str(config.get("model") or os.getenv("VOICE_WHISPER_MODEL", "base"))
            provider = str(config.get("provider") or os.getenv("VOICE_STT_PROVIDER", "whisper"))

            result = transcribe_audio(
                file_path=file_path,
                language=language,
                model=model,
                provider=provider,
            )
            return _ok(action=action, result=result, t0=t0)

        if action == "synthesize":
            text = payload.get("text")
            if not text or not isinstance(text, str) or not text.strip():
                return _error("Missing non-empty 'text' for synthesize.", action=action, t0=t0)

            output_path = payload.get("output_path")
            model_name = config.get("model_name") or os.getenv("VOICE_TTS_MODEL", "")
            speaker_wav = config.get("speaker_wav")
            provider = str(config.get("provider") or os.getenv("VOICE_TTS_PROVIDER", "coqui"))

            result = synthesize_speech(
                text=text.strip(),
                output_path=output_path if isinstance(output_path, str) and output_path else None,
                model_name=str(model_name).strip() if model_name else None,
                speaker_wav=str(speaker_wav).strip() if isinstance(speaker_wav, str) and speaker_wav else None,
                provider=provider,
            )
            return _ok(action=action, result=result, t0=t0)

        return _error("Unexpected router state.", action=action, t0=t0)

    except Exception as e:
        return _error(f"Unhandled error: {type(e).__name__}: {e}", action=action, t0=t0)


def _ok(*, action: str, result: Dict[str, Any], t0: float) -> Dict[str, Any]:
    return {
        "ok": True,
        "status": "success",
        "action": action,
        "result": result,
        "meta": {"latency_ms": int((time.time() - t0) * 1000)},
    }


def _error(message: str, *, action: Optional[str], t0: float) -> Dict[str, Any]:
    return {
        "ok": False,
        "status": "error",
        "action": action,
        "error": message,
        "meta": {"latency_ms": int((time.time() - t0) * 1000)},
    }
