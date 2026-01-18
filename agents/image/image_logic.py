from __future__ import annotations
from typing import Any, Dict

from .schemas.payloads import AgentPayload, ExtractTextConfig
from .loaders.image_loader import load_image_from_path
from .loaders.pdf_loader import pdf_to_images_from_path
from .engines.ocr_engine import OcrEngine
from .engines.object_engine import ObjectEngine
from .utils.text import normalize_text
from .models.model import LayoutLMv3Extractor


def process(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        req = AgentPayload.model_validate(payload)
        cfg_dict = req.config or {}
        cfg = ExtractTextConfig.model_validate(cfg_dict) if req.action == "extract_text" else None

        if req.action == "extract_text":
            # 1) cargar páginas
            if req.file_path.lower().endswith(".pdf"):
                pages = pdf_to_images_from_path(req.file_path, max_pages=cfg.max_pages, dpi=cfg.dpi)
                file_type = "pdf"
            else:
                pages = [load_image_from_path(req.file_path)]
                file_type = "image"

            # 2) OCR
            ocr = OcrEngine()
            page_texts = []
            for img in pages:
                raw = ocr.extract_text_from_image(img, language=cfg.language) if cfg.use_ocr else ""
                page_texts.append(normalize_text(raw))

            normal_text = "\n".join([t for t in page_texts if t]).strip()

            result: Dict[str, Any] = {
                "status": "success",
                "normal_text": normal_text,
                "metadata": {
                    "page_count": len(pages),
                    "file_type": file_type,
                    "used_ocr": cfg.use_ocr,
                    "language": cfg.language,
                },
            }

            # 3) LayoutLMv3 opcional (fase 2)
            if cfg.use_layoutlmv3 and normal_text:
                ie = LayoutLMv3Extractor(model_name=cfg.layoutlmv3_model)
                result["structured"] = ie.extract(pages[0], normal_text)  # ejemplo simple

            return result

        if req.action == "detect_objects":
            # placeholder
            img = load_image_from_path(req.file_path)
            objects = ObjectEngine().detect(img)
            return {"status": "success", "objects": objects, "metadata": {"file_type": "image"}}

        return {"status": "error", "error": f"Acción no soportada: {req.action}"}

    except Exception as e:
        return {"status": "error", "error": str(e)}
