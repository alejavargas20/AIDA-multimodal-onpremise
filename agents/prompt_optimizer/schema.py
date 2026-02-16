# aida-multimodal-onpremise/agents/prompt_optimizer/schema.py
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union
import json

from pydantic import BaseModel, Field, model_validator


InputSource = Literal["chat", "stt", "ocr", "unknown"]

AgentName = Literal["nlp", "data", "image", "voice", "report"]

StatusName = Literal["ok", "needs_clarification", "error"]

class Metadata(BaseModel):
    language: str = Field(default="unknown", min_length=2)
    input_source: InputSource = "unknown"

class Task(BaseModel):
    agent: AgentName
    action: str = Field(..., min_length=1, description="Verb-only action name (no agent prefix).")
    input: Union[str, Dict[str, Any]] = Field(..., description="Business-level input (no SQL). Can be str or dict.")
    params: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def no_sql_in_input(self) -> "Task":
        # Guardrail: tasks should NOT include SQL or explicit table names
        raw = self.input
        as_text = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
        lowered = (as_text or "").lower()
        forbidden = ["select ", " from ", " join ", " where ", " group by", "insert ", "update ", "delete "]
        if any(tok in lowered for tok in forbidden):
            raise ValueError("Task.input appears to contain SQL, which is forbidden in Prompt Optimizer tasks.")
        return self


class IntentPlan(BaseModel):
    intent: str = Field(..., min_length=1)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    tasks: List[Task] = Field(default_factory=list, max_length=3)
    metadata: Metadata = Field(default_factory=Metadata)
    conductual_state: Optional[dict] = None
    conductual_notes: Optional[str] = None


class PromptOptimizerResponse(BaseModel):
    optimized_prompt: str = Field(..., min_length=1)
    intent_plan: IntentPlan
    status: StatusName = "ok"
    errors: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_minimum_contract(self) -> "PromptOptimizerResponse":
        # Minimal contract: intent + tasks must exist (inside intent_plan)
        if not self.intent_plan.intent:
            raise ValueError("intent_plan.intent is required.")
        if self.intent_plan.tasks is None:
            raise ValueError("intent_plan.tasks is required (can be empty list).")
        return self

