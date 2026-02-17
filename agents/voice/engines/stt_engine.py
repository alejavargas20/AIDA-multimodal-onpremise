# # aida-multimodal-onpremise/agents/voice/engines/stt_engine.py
# from __future__ import annotations

# import os
# import sys
# from typing import Any, Dict, List

# os.environ["OMP_NUM_THREADS"] = "4"
# os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"



# def get_whisper_model():
#     """Obtiene o inicializa el motor Faster-Whisper de forma segura."""
#     if "WHISPER_INSTANCE" not in sys.modules or sys.modules["WHISPER_INSTANCE"] is None:
#         print("\n[STT] Primer audio detectado. Inicializando Faster-Whisper 'small' en CPU...")
#         try:
#             from faster_whisper import WhisperModel
            
#             model = WhisperModel(
#                 "small", 
#                 device="cpu", 
#                 compute_type="float32", 
#                 cpu_threads=2
#             )
            
#             sys.modules["WHISPER_INSTANCE"] = model
#             print("[STT] Modelo Faster-Whisper cargado y listo para transcribir.")
#         except Exception as e:
#             print(f"[STT WARNING] Error crítico cargando Faster-Whisper: {e}")
#             raise e
            
#     return sys.modules["WHISPER_INSTANCE"]


# def transcribe_audio(
#     *,
#     file_path: str,
#     language: str = "es",
#     model: str = "small",  
#     provider: str = "whisper",
# ) -> Dict[str, Any]:
#     """
#     STT: audio -> texto.
#     """
#     provider = (provider or "whisper").strip().lower()

#     if provider == "mock" or os.getenv("VOICE_FORCE_MOCK", "").lower() in {"1", "true", "yes"}:
#         return {
#             "text": "(mock) Transcripción simulada.",
#             "segments": [],
#             "language": language,
#             "provider": "mock",
#             "model": model,
#         }

#     if provider != "whisper":
#         raise RuntimeError(f"Unsupported STT provider: {provider}")

#     stt_model = get_whisper_model()

#     try:
#         segments_generator, info = stt_model.transcribe(file_path, language=language)

#         text_parts = []
#         safe_segments = []

#         for segment in segments_generator:
#             text_parts.append(segment.text)
#             safe_segments.append({
#                 "start": segment.start,
#                 "end": segment.end,
#                 "text": segment.text,
#             })

#         full_text = "".join(text_parts).strip()

#         if "temp_uploads" in file_path and os.path.exists(file_path):
#             try:
#                 os.remove(file_path)
#                 print(f"[STT] Archivo temporal eliminado: {file_path}")
#             except Exception as e:
#                 print(f"[STT WARNING] No se pudo borrar el temporal: {e}")

#         return {
#             "text": full_text,
#             "segments": safe_segments,
#             "language": info.language if info else language,
#             "provider": "whisper",
#             "model": model,
#         }
#     except Exception as e:
#         print(f"[STT ERROR] Fallo en transcripción: {e}")
#         raise e


# aida-multimodal-onpremise/agents/voice/engines/stt_engine.py
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

# Variables de entorno para estabilidad en Windows
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

def get_whisper_model():
    """Obtiene o inicializa el motor Whisper oficial de forma segura."""
    if "WHISPER_INSTANCE" not in sys.modules or sys.modules["WHISPER_INSTANCE"] is None:
        print("\n[STT] Primer audio detectado. Inicializando Whisper 'turbo' en CPU...")
        try:
            import whisper # type: ignore
            
            # Usamos el modelo 'turbo' de OpenAI
            model = whisper.load_model("turbo", device="cpu")
            
            sys.modules["WHISPER_INSTANCE"] = model
            print("[STT] Modelo Whisper cargado y listo para transcribir.")
        except ImportError:
             print("[STT ERROR] Falta la librería. Instala: pip install openai-whisper")
             raise
        except Exception as e:
            print(f"[STT WARNING] Error crítico cargando Whisper: {e}")
            raise e
            
    return sys.modules["WHISPER_INSTANCE"]


def transcribe_audio(
    *,
    file_path: str,
    language: str = "es",
    model: str = "turbo",  
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

    stt_model = get_whisper_model()

    try:
        # Transcripción con el Whisper oficial
        result = stt_model.transcribe(file_path, language=language, task="transcribe")

        text = (result or {}).get("text") or ""
        segments = (result or {}).get("segments") or []
        safe_segments: List[Dict[str, Any]] = []

        for s in segments:
            if isinstance(s, dict):
                safe_segments.append({
                    "start": s.get("start"),
                    "end": s.get("end"),
                    "text": s.get("text"),
                })

        # Limpieza del archivo temporal
        if "temp_uploads" in file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"[STT] Archivo temporal eliminado: {file_path}")
            except Exception as e:
                print(f"[STT WARNING] No se pudo borrar el temporal: {e}")

        return {
            "text": text.strip(),
            "segments": safe_segments,
            "language": language,
            "provider": "whisper",
            "model": model,
        }
    except Exception as e:
        print(f"[STT ERROR] Fallo en transcripción: {e}")
        raise e