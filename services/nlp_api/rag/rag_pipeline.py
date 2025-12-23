import os
import time
from typing import Any, Dict, List, Tuple

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from app.llm_client import chat_ollama

CHROMA_DIR = os.getenv("CHROMA_DIR", "data/chroma")
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

DEFAULT_TOP_K = int(os.getenv("TOP_K", "4"))


def _get_vectorstore() -> Chroma:
    emb = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return Chroma(persist_directory=CHROMA_DIR, embedding_function=emb)


def _docs_to_used_docs(docs) -> List[Dict[str, Any]]:
    used = []
    for d in docs:
        md = d.metadata or {}
        used.append(
            {
                "source": md.get("source", md.get("file_path", "unknown")),
                "page": md.get("page", None),
                "snippet": (d.page_content or "")[:300],
            }
        )
    return used


def answer_with_rag(
    question: str,
    history: List[Dict[str, str]] | None = None,
    retrieval: bool = True,
    top_k: int | None = None,
) -> Tuple[str, List[Dict[str, Any]], int]:
    """
    Devuelve: (answer, used_docs, elapsed_ms)
    - retrieval=False => NO usa Chroma, used_docs=[]
    """
    t0 = time.time()
    history = history or []
    k = top_k or DEFAULT_TOP_K

    context = ""
    retrieved_docs = []

    if retrieval:
        vs = _get_vectorstore()
        retrieved_docs = vs.similarity_search(question, k=k)

        #  bloque de contexto para el prompt
        pieces = []
        for i, d in enumerate(retrieved_docs, start=1):
            md = d.metadata or {}
            src = md.get("source", md.get("file_path", "unknown"))
            page = md.get("page", None)
            header = f"[{i}] source={src}" + (f" page={page}" if page is not None else "")
            pieces.append(header + "\n" + (d.page_content or ""))
        context = "\n\n".join(pieces)

    # Prompt: con o sin contexto
    system = (
        "Eres un asistente NLP para documentación financiera. "
        "Responde de forma concisa y basada en el contexto cuando exista. "
        "Si no hay contexto suficiente, dilo explícitamente."
    )

    if retrieval and context.strip():
        user = (
            "Usa SOLO el siguiente CONTEXTO para responder.\n\n"
            f"CONTEXTO:\n{context}\n\n"
            f"PREGUNTA:\n{question}\n"
        )
    else:
        user = (
            "Responde sin usar base documental (modo sin retrieval). "
            "Si no puedes asegurar algo, dilo.\n\n"
            f"PREGUNTA:\n{question}\n"
        )

    messages = [{"role": "system", "content": system}]
    
    for h in history:
        if "role" in h and "content" in h:
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user})

    answer = chat_ollama(messages)

    used_docs = _docs_to_used_docs(retrieved_docs) if retrieval else []
    elapsed_ms = int((time.time() - t0) * 1000)
    return answer, used_docs, elapsed_ms
