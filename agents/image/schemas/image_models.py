from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

InputType = Literal["image", "pdf"]

class ImageAgentOptions(BaseModel):
    language_hint: Optional[str] = Field(default=None, description="Ej: 'es', 'en'")
    max_pages: int = Field(default=10, ge=1, le=200)
    run_ocr: bool = True
    run_llm_structuring: bool = True
    preprocess: bool = True  # placeholder

class ImageAgentRequest(BaseModel):
    input_type: InputType
    path: Optional[str] = None
    content_bytes: Optional[bytes] = None
    user_prompt: str = ""
    options: ImageAgentOptions = Field(default_factory=ImageAgentOptions)

class ExtractedPage(BaseModel):
    page_num: int
    text: str

class ImageAgentResult(BaseModel):
    normalized_text: str
    extracted: Dict[str, Any]
    routing_hints: Dict[str, Any]
    diagnostics: Dict[str, Any]
