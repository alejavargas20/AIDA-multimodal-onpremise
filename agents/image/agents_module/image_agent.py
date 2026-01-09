from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List

from agents.image.schemas.image_models import (
    ImageAgentRequest, ImageAgentResult, ExtractedPage
)
from agents.image.engines.ocr_engine import OcrEngine
from agents.image.llm.llm_client import LlmClient
from agents.image.utils.text import normalize_text
from agents.image.utils.heuristics import guess_doc_type, basic_text_quality_metrics
from agents.image.utils.ids import stable_content_id
from agents.image.loaders.image_loader import load_image_from_path, load_image_from_bytes
from agents.image.loaders.pdf_loader import pdf_to_images_from_path, pdf_to_images_from_bytes

import time

@dataclass
class ImageAgent:
    ocr: OcrEngine
    llm: LlmClient

    def run(self, req: ImageAgentRequest) -> ImageAgentResult:
        t0 = time.time()
        content_id = stable_content_id(req)

        if not req.path and req.content_bytes is None:
            raise ValueError("ImageAgentRequest requiere 'path' o 'content_bytes'")

        # A) Load / convert
        t_load = time.time()
        pages: List[Any] = []

        if req.input_type == "image":
            pages = [load_image_from_path(req.path)] if req.path else [load_image_from_bytes(req.content_bytes or b"")]
        elif req.input_type == "pdf":
            pages = (
                pdf_to_images_from_path(req.path, req.options.max_pages)
                if req.path else
                pdf_to_images_from_bytes(req.content_bytes or b"", req.options.max_pages)
            )
        else:
            raise ValueError(f"input_type no soportado: {req.input_type}")

        load_ms = int((time.time() - t_load) * 1000)

        # B) OCR
        t_ocr = time.time()
        extracted_pages: List[ExtractedPage] = []
        full_text_parts: List[str] = []

        if req.options.run_ocr:
            for idx, page_img in enumerate(pages, start=1):
                raw = self.ocr.extract_text_from_image(page_img, req.options.language_hint)
                cleaned = normalize_text(raw)
                extracted_pages.append(ExtractedPage(page_num=idx, text=cleaned))
                if cleaned:
                    full_text_parts.append(f"[PAGE {idx}]\n{cleaned}")
        else:
            extracted_pages = [ExtractedPage(page_num=i, text="") for i in range(1, len(pages) + 1)]

        full_text = normalize_text("\n\n".join(full_text_parts))
        ocr_ms = int((time.time() - t_ocr) * 1000)

        # C) Heuristics + metrics
        t_heur = time.time()
        doc_type_guess = guess_doc_type(full_text)
        metrics = basic_text_quality_metrics(full_text)
        heur_ms = int((time.time() - t_heur) * 1000)

        routing_hints: Dict[str, Any] = {
            "content_id": content_id,
            "has_text": bool(full_text),
            "pages": len(pages),
            "doc_type_guess": doc_type_guess,
            "recommended_agents": ["nlp"] if full_text else ["image"],
        }

        # D) LLM structuring (optional)
        t_llm = time.time()
        doc_schema: Dict[str, Any] = {}

        if req.options.run_llm_structuring and full_text:
            system_prompt = (
                "Eres un extractor de información de documentos. "
                "Devuelve JSON ESTRICTO con: doc_type, language, key_points(list), entities(list), suggested_next_agents(list)."
            )
            user_prompt = (
                f"Petición: {req.user_prompt}\n\n"
                f"Texto OCR:\n{full_text}\n\n"
                "Devuelve SOLO JSON válido."
            )
            doc_schema = self.llm.complete_json(system_prompt, user_prompt)

            if isinstance(doc_schema.get("doc_type"), str) and doc_schema["doc_type"]:
                routing_hints["doc_type_llm"] = doc_schema["doc_type"]
            if isinstance(doc_schema.get("suggested_next_agents"), list) and doc_schema["suggested_next_agents"]:
                routing_hints["recommended_agents"] = doc_schema["suggested_next_agents"]

        llm_ms = int((time.time() - t_llm) * 1000)

        # E) normalized_text (lo que consume el orquestador)
        brief = ""
        kps = doc_schema.get("key_points")
        if isinstance(kps, list) and kps:
            brief = "Key points:\n- " + "\n- ".join(str(x) for x in kps[:10])

        normalized_text = normalize_text("\n\n".join([brief, full_text]).strip())

        total_ms = int((time.time() - t0) * 1000)

        return ImageAgentResult(
            normalized_text=normalized_text,
            extracted={
                "full_text": full_text,
                "pages": [p.model_dump() for p in extracted_pages],
                "doc_schema": doc_schema,
                "metrics": metrics,
            },
            routing_hints=routing_hints,
            diagnostics={"timings_ms": {"load": load_ms, "ocr": ocr_ms, "heuristics": heur_ms, "llm": llm_ms, "total": total_ms}},
        )
