# aida-multimodal-onpremise/agents/prompt_optimizer/exceptions.py

class PromptOptimizerError(Exception):
    """Base exception for Prompt Optimizer."""


class ValidationError(PromptOptimizerError):
    """Raised when output JSON fails validation."""


class PlanningError(PromptOptimizerError):
    """Raised when planner cannot produce a valid plan."""
