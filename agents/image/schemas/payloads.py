# aida-multimodal-onpremise/agents/image/schemas/payloads.py
from __future__ import annotations
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field

ActionType = Literal["extract_text", "detect_objects"]

class ExtractTextConfig(BaseModel):
    use_ocr: bool = True
    language: str = "es"
    max_pages: int = Field(default=10, ge=1, le=200)
    dpi: int = Field(default=200, ge=72, le=400)

    use_layoutlmv3: bool = False
    layoutlmv3_model: str = "microsoft/layoutlmv3-base"

class AgentPayload(BaseModel):
    action: ActionType
    file_path: str
    config: Optional[Dict[str, Any]] = None
