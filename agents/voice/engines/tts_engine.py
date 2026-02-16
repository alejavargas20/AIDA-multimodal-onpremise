# from __future__ import annotations

# import os
# from typing import Any, Dict, Optional

# from ..utils.audio import ensure_parent_dir, default_tts_output_path


# def synthesize_speech(
#     *,
#     text: str,
#     output_path: Optional[str] = None,
#     model_name: Optional[str] = None,
#     speaker_wav: Optional[str] = None,
#     provider: str = "coqui",
# ) -> Dict[str, Any]:
#     """
#     TTS: texto -> audio (.wav)

#     provider:
#       - coqui: Coqui TTS (pip install TTS)
#       - pyttsx3: fallback simple CPU (pip install pyttsx3)
#       - mock: no genera audio real (para tests)

#     model_name (opcional):
#       - si no viene, usamos una opción por defecto razonable.
#     """
#     provider = (provider or "coqui").strip().lower()

#     if provider == "mock" or os.getenv("VOICE_FORCE_MOCK", "").lower() in {"1", "true", "yes"}:
#         out = output_path or default_tts_output_path()
#         ensure_parent_dir(out)
#         return {
#             "audio_path": out,
#             "provider": "mock",
#             "model_name": model_name or "",
#             "note": "TTS mock: no se generó audio real.",
#         }

#     if not output_path:
#         output_path = default_tts_output_path()
#     ensure_parent_dir(output_path)

#     if provider == "pyttsx3":
#         return _tts_pyttsx3(text=text, output_path=output_path)

#     if provider == "coqui":
#         return _tts_coqui(text=text, output_path=output_path, model_name=model_name, speaker_wav=speaker_wav)

#     raise RuntimeError(f"Unsupported TTS provider: {provider}")


# def _tts_pyttsx3(*, text: str, output_path: str) -> Dict[str, Any]:
#     try:
#         import pyttsx3  # type: ignore
#     except Exception as e:
#         raise RuntimeError("TTS provider 'pyttsx3' no disponible. Instala: pip install pyttsx3") from e

#     engine = pyttsx3.init()
#     engine.save_to_file(text, output_path)
#     engine.runAndWait()

#     return {"audio_path": output_path, "provider": "pyttsx3", "model_name": ""}


# def _tts_coqui(*, text: str, output_path: str, model_name: Optional[str], speaker_wav: Optional[str]) -> Dict[str, Any]:
#     try:
#         from TTS.api import TTS  # type: ignore
#     except Exception as e:
#         raise RuntimeError("TTS provider 'coqui' no disponible. Instala: pip install TTS") from e

#     default_model = "tts_models/multilingual/multi-dataset/xtts_v2"
#     chosen_model = (model_name or default_model).strip()

#     use_gpu = False
#     try:
#         import torch  # type: ignore
#         use_gpu = bool(torch.cuda.is_available())
#     except Exception:
#         use_gpu = False

#     tts = TTS(model_name=chosen_model, progress_bar=False, gpu=use_gpu)

#     # XTTS permite speaker_wav para “clonar” timbre (opcional)
#     if speaker_wav:
#         tts.tts_to_file(text=text, file_path=output_path, speaker_wav=speaker_wav, language="es")
#     else:
#         tts.tts_to_file(text=text, file_path=output_path)

#     return {"audio_path": output_path, "provider": "coqui", "model_name": chosen_model, "gpu": use_gpu}
