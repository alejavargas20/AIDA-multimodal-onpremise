from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel
from typing import List, Optional, Literal, Any, Dict
import logging
import requests
from app.logger import append_log
from rag.rag_pipeline import answer_with_rag
import os

app = FastAPI(title="AIDA NLP Agent", version="0.1")

# Logs en consola 
logger = logging.getLogger("aida_nlp_api")
logging.basicConfig(level=logging.INFO)


class HistoryMsg(BaseModel):
    role: Literal["user", "assistant"]
    content: str



class NLPAnswerRequest(BaseModel):
    question: str
    history: Optional[List[HistoryMsg]] = None
    retrieval: bool = True
    top_k: int = 4
    input_source: Literal["chat", "stt", "ocr"] = "chat"
    language: Optional[str] = "es"


class NLPAnswerResponse(BaseModel):
    answer: str
    used_docs: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    conductual_state: Optional[Dict[str, Any]] = None
    conductual_notes: Optional[str] = None


@app.post("/nlp/answer", response_model=NLPAnswerResponse)
def nlp_answer(req: NLPAnswerRequest):
    try:
        answer, used_docs, elapsed_ms = answer_with_rag(
            question=req.question,
            history=[h.model_dump() for h in (req.history or [])],
            retrieval=req.retrieval,
            top_k=req.top_k,
        )

        metadata = {
            "language": req.language,
            "input_source": req.input_source,
            "processing_time_ms": elapsed_ms,
        }

        append_log(
                {
                    "question": req.question,
                    "retrieval": req.retrieval,
                    "used_docs": used_docs,
                    "latency_ms": elapsed_ms,
                    "model": os.getenv("MODEL_NAME", "unknown"),
                }
            )
        
        return NLPAnswerResponse(
            answer=answer,
            used_docs=used_docs,
            metadata=metadata,
            conductual_state=None,
            conductual_notes=None,
        )

    # Ollama no accesible 
    except requests.exceptions.ConnectionError:
        logger.exception("Ollama no responde (ConnectionError)")
        raise HTTPException(
            status_code=503,
            detail=(
                "El motor LLM (Ollama) no está disponible. "
                "Comprueba que Ollama está encendido en Windows y que "
                "OLLAMA_HOST permite acceso desde WSL."
            ),
        )

    # Ollama respondió pero con error 
    except requests.exceptions.HTTPError as e:
        logger.exception("Ollama devolvió HTTPError")
        raise HTTPException(
            status_code=502,
            detail=f"Error del motor LLM (Ollama): {str(e)}",
        )

    # Timeouts de red 
    except requests.exceptions.Timeout:
        logger.exception("Timeout al llamar a Ollama")
        raise HTTPException(
            status_code=504,
            detail="Timeout al comunicarse con el motor LLM (Ollama). Inténtalo de nuevo.",
        )

    except Exception as e:
        logger.exception("Error inesperado en /nlp/answer")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servicio NLP: {type(e).__name__}: {str(e)}",
        )
