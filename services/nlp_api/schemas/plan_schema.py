from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, conlist, confloat


class Intent(str, Enum):
    consulta_datos = "consulta_datos"
    analisis_financiero = "analisis_financiero"
    resumen = "resumen"
    explicacion = "explicacion"
    comparacion = "comparacion"
    recomendacion = "recomendacion"
    alerta_riesgo = "alerta_riesgo"
    perfil_cliente = "perfil_cliente"
    procesar_documento = "procesar_documento"
    ayuda = "ayuda"
    otro = "otro"


class Agent(str, Enum):
    nlp = "nlp"
    data = "data"
    image = "image"
    voice = "voice"


class InputSource(str, Enum):
    chat = "chat"
    stt = "stt"
    ocr = "ocr"


class Action(str, Enum):
    preguntar_aclaracion = "preguntar_aclaracion"
    responder = "responder"
    resumir = "resumir"
    extraer_entidades = "extraer_entidades"
    consultar = "consultar"
    generar_reporte = "generar_reporte"
    describir_imagen = "describir_imagen"
    extraer_texto_documento = "extraer_texto_documento"
    transcribir_audio = "transcribir_audio"
    otro = "otro"


class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str = Field(..., description="ISO-639-1 (ej: es, en).")
    input_source: InputSource = Field(..., description="Origen del input normalizado.")


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: Agent
    action: Action
    input: str = Field(..., min_length=1, max_length=4000)
    params: Dict[str, Any] = Field(default_factory=dict)


class PlannerOutput(BaseModel):
    """
    Contrato oficial entre Prompt Enhancer (planner) y el orquestador.
    En el MVP: conductual_state y conductual_notes deben ser null.
    """
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    confidence: float = Field(0.5, ge=0.0, le=1.0)

    tasks: List[Task] = Field(..., min_length=1)   
    metadata: Metadata

    conductual_state: Optional[Dict[str, Any]] = None
    conductual_notes: Optional[str] = None
