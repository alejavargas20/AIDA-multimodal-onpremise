# aida-multimodal-onpremise/agents/image/image_logic.py
from __future__ import annotations
from typing import Any, Dict

from agents.image.schemas.payloads import AgentPayload, ExtractTextConfig
from agents.image.loaders.image_loader import load_image_from_path
from agents.image.loaders.pdf_loader import pdf_to_images_from_path
from agents.image.engines.ocr_engine import OcrEngine
from agents.image.utils.text import postprocess_ocr_text, normalize_text
#from models.model import LayoutLMv3Extractor

import os
import pypdfium2 as pdfium


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

        file_type = "pdf" if file_path.lower().endswith(".pdf") else "image"

        raw_text = ""
        page_count = 0

        if file_type == "pdf":
            pdf = pdfium.PdfDocument(file_path)
            n_pages = min(len(pdf), max_pages)
            pdf_texts = []
            
            for i in range(n_pages):
                text_page = pdf[i].get_textpage()
                page_string = text_page.get_text_range()
                if page_string:
                    pdf_texts.append(page_string)
            
            raw_text = "\n\n".join(pdf_texts).strip()
            page_count = n_pages

        if not raw_text:
            images = pdf_to_images_from_path(file_path, max_pages=max_pages, dpi=dpi) if file_type == "pdf" else [load_image_from_path(file_path)]
            
            ocr_engine = OcrEngine()
            page_texts = []
            
            for img in images:
                raw = ocr_engine.extract_text_from_image(img, language=language)
                
                if file_type == "pdf":
                    cleaned = normalize_text(raw)
                    page_texts.append(cleaned)
                else:
                    cleaned = postprocess_ocr_text(raw)
                    page_texts.append(cleaned)

            raw_text = "\n\n".join(page_texts)
            page_count = len(images)

        return {
            "status": "success",
            "normal_text": raw_text,
            "metadata": {
                "page_count": page_count,
                "file_type": file_type,
                "language": language,
                "dpi": dpi
            }
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}