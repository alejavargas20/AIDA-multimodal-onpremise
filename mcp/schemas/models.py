# mcp/schemas/models.py

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

# MCP request


class ToolRequest(BaseModel):
    tool_name: str = Field(
        ...,
        description="Nombre de la tool registrada en el MCP"
    )
    payload: Dict[str, Any] = Field(
        ...,
        description="Datos de entrada para la tool"
    )

# Prompt Optimizer output

class Task(BaseModel):
    agent: str = Field(
        ...,
        description="Agente que debe ejecutar la tarea (data, nlp, voice, etc.)"
    )
    action: str = Field(
        ...,
        description="Acción declarativa que debe ejecutar el agente"
    )
    input: Dict[str, Any] = Field(
        ...,
        description="Parámetros de la tarea"
    )

class IntentPlan(BaseModel):
    intent: str = Field(
        ...,
        description="Intención global de la solicitud"
    )
    tasks: List[Task] = Field(
        ...,
        description="Plan ordenado de ejecución"
    )

class PromptOptimizerResponse(BaseModel):
    optimized_prompt: str = Field(
        ...,
        description="Prompt reescrito y optimizado"
    )
    intent_json: IntentPlan = Field(
        ...,
        description="Plan de tareas para el orquestador"
    )
    status: str = Field(
        ...,
        description="Estado del procesamiento"
    )

# Generic Agent Output

class AgentResponse(BaseModel):
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Resultado del agente"
    )
    status: str = Field(
        ...,
        description="Estado de la ejecución del agente"
    )
