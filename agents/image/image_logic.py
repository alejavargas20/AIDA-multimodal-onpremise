from __future__ import annotations
from typing import Any, Dict

from schemas.payloads import AgentPayload, ExtractTextConfig
from loaders.image_loader import load_image_from_path
from loaders.pdf_loader import pdf_to_images_from_path
from engines.ocr_engine import OcrEngine
from utils.text import postprocess_ocr_text, normalize_text
#from models.model import LayoutLMv3Extractor

import os
import pytesseract

def process(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        action = payload.get("action")
        file_path = payload.get("file_path")
        config = payload.get("config") or {}

        if action != "extract_text":
            return {"status": "error", "error": "Solo se soporta action='extract_text'."}
        if not file_path:
            return {"status": "error", "error": "Falta file_path."}
        if not os.path.exists(file_path):
            return {"status": "error", "error": f"No existe el archivo: {file_path}"}

        language = config.get("language", "es")
        max_pages = int(config.get("max_pages", 10))
        dpi = int(config.get("dpi", 300))

        lang = "spa" if language in ("es", "spa") else language
        file_type = "pdf" if file_path.lower().endswith(".pdf") else "image"

        images = pdf_to_images_from_path(file_path, max_pages=max_pages, dpi=dpi) if file_type == "pdf" else [load_image_from_path(file_path)]

        page_texts = []
        for img in images:
            if file_type == "pdf":
                raw = pytesseract.image_to_string(img, lang=lang)
                cleaned = normalize_text(raw)
                page_texts.append(cleaned)
            else:
                raw = pytesseract.image_to_string(img, lang=lang)
                cleaned = postprocess_ocr_text(raw)
                page_texts.append(cleaned)

        raw_text = "\n\n".join(page_texts)

        return {
            "status": "success",
            "normal_text": raw_text,
            "metadata": {
                "page_count": len(images),
                "file_type": file_type,
                "language": language,
                "dpi": dpi
            }
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}
