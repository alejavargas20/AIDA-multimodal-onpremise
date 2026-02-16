# aida-multimodal-onpremise/agents/voice/engines/stt_engine.py
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

# =====================================================================
# BARRERA DE PROTECCIÓN C++ (ANTI-SEGFAULT)
# =====================================================================
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# =====================================================================
# CARGA PEREZOSA (LAZY LOADING)
# Ya no cargamos el modelo globalmente al arrancar el servidor.
# Lo cargaremos SOLO cuando llegue el primer audio.
# =====================================================================

def get_whisper_model():
    """Obtiene o inicializa el motor Faster-Whisper de forma segura."""
    if "WHISPER_INSTANCE" not in sys.modules or sys.modules["WHISPER_INSTANCE"] is None:
        print("\n[STT] Primer audio detectado. Inicializando Faster-Whisper 'medium' en CPU...")
        try:
            from faster_whisper import WhisperModel
            
            # Usamos int8 para que ocupe poca RAM (tu PC tiene 16GB en total)
            model = WhisperModel(
                "medium", 
                device="cpu", 
                compute_type="int8", 
                cpu_threads=4
            )
            
            sys.modules["WHISPER_INSTANCE"] = model
            print("[STT] Modelo Faster-Whisper cargado y listo para transcribir.")
        except Exception as e:
            print(f"[STT WARNING] Error crítico cargando Faster-Whisper: {e}")
            raise e
            
    return sys.modules["WHISPER_INSTANCE"]


def transcribe_audio(
    *,
    file_path: str,
    language: str = "es",
    model: str = "medium",  
    provider: str = "whisper",
) -> Dict[str, Any]:
    """
    STT: audio -> texto.
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

    # 🚀 AQUÍ LLAMAMOS A LA CARGA PEREZOSA 🚀
    stt_model = get_whisper_model()

    # Transcripción con Faster-Whisper
    segments_generator, info = stt_model.transcribe(file_path, language=language)

    text_parts = []
    safe_segments: List[Dict[str, Any]] = []

    # Extraemos el texto del generador
    for segment in segments_generator:
        text_parts.append(segment.text)
        safe_segments.append(
            {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
            }
        )

    full_text = "".join(text_parts).strip()

    return {
        "text": full_text,
        "segments": safe_segments,
        "language": info.language if info else language,
        "provider": "whisper",
        "model": model,
    }