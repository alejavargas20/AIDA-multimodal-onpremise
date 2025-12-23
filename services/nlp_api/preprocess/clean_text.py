from __future__ import annotations

import re
import unicodedata
from typing import Dict, Literal

InputSource = Literal["chat", "stt", "ocr"]

# Stopwords mínimas para detección ES/EN 
_ES_STOPWORDS = {
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por", "un", "para",
    "con", "no", "una", "su", "al", "lo", "como", "más", "pero", "sus", "ya", "o", "este",
    "sí", "porque", "esta", "entre", "cuando", "muy", "sin", "sobre", "también"
}
_EN_STOPWORDS = {
    "the", "and", "to", "of", "in", "is", "it", "you", "that", "for", "on", "with", "as", "are",
    "this", "was", "be", "at", "or", "by", "an", "from", "but", "not", "we", "they", "have"
}

_FILLERS_ES = [
    "eh", "em", "mmm", "mm", "este", "o sea", "pues", "bueno", "digamos", "verdad"
]

_ZERO_WIDTH = ["\u200b", "\u200c", "\u200d", "\ufeff"]


def normalize_text(text: str) -> str:
    """
    - Normaliza unicode (NFKC)
    - Limpia espacios raros / zero-width
    - Normaliza saltos de línea
    - Colapsa espacios múltiples
    """
    if text is None:
        return ""

    # Unicode normalize
    t = unicodedata.normalize("NFKC", str(text))

    # Quitar chars invisibles
    for z in _ZERO_WIDTH:
        t = t.replace(z, "")

    # Reemplazar NBSP por espacio normal
    t = t.replace("\u00A0", " ")

    # Normalizar newlines
    t = t.replace("\r\n", "\n").replace("\r", "\n")

    # Colapsar espacios (pero conservando \n)
    # Primero reemplaza tabs por espacio
    t = t.replace("\t", " ")
    # Colapsa espacios múltiples
    t = re.sub(r"[ ]{2,}", " ", t)

    # Quitar espacios al inicio/fin de líneas
    t = "\n".join(line.strip() for line in t.split("\n"))

    # Colapsar líneas vacías excesivas (máximo 2)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()

    return t


def reduce_stt_noise(text: str) -> str:
    """
    Limpieza típica STT:
    - elimina muletillas repetidas
    - colapsa palabras repetidas ("eh eh", "mmm mmm")
    """
    t = text

    # Eliminar muletillas (repetidas o sueltas) manteniendo el resto
    for filler in _FILLERS_ES:
        # ej: "eh eh eh" o " eh " -> " "
        pattern = r"(?:\b" + re.escape(filler) + r"\b(?:\s+|$))+"
        t = re.sub(pattern, " ", t, flags=re.IGNORECASE)

    # Colapsar palabras repetidas consecutivas: "hola hola" -> "hola"
    t = re.sub(r"\b(\w+)(?:\s+\1\b)+", r"\1", t, flags=re.IGNORECASE)

    # Limpiar espacios
    t = re.sub(r"[ ]{2,}", " ", t).strip()
    return t


def reduce_ocr_noise(text: str) -> str:
    """
    Limpieza típica OCR:
    - une palabras cortadas por guión al final de línea: "infor-\nmación" -> "información"
    - convierte saltos de línea “rotos” en espacios cuando parece frase continua
    - corrige confusiones comunes en tokens numéricos (l/I -> 1, O -> 0) solo en contexto de dígitos
    """
    t = text

    # Unir palabras cortadas por guión + newline
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)

    # Reemplazar saltos de línea dentro de párrafos por espacio (si no hay doble salto)
    t = re.sub(r"(?<!\n)\n(?!\n)", " ", t)

    # Colapsar espacios
    t = re.sub(r"[ ]{2,}", " ", t).strip()

    # Correcciones numéricas:
    # "l" o "I" dentro de números -> "1" (ej: 1l00 -> 1100)
    t = re.sub(r"(?<=\d)[lI](?=\d)", "1", t)
    # "O" dentro de números -> "0" (ej: 2O25 -> 2025)
    t = re.sub(r"(?<=\d)O(?=\d)", "0", t)

    return t


def detect_language(text: str) -> str:
    """
    Heurística ES/EN por conteo de stopwords.
    Devuelve: "es" o "en"
    """
    tokens = re.findall(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+", text.lower())
    if not tokens:
        return "es"

    es_hits = sum(1 for w in tokens if w in _ES_STOPWORDS)
    en_hits = sum(1 for w in tokens if w in _EN_STOPWORDS)

    if es_hits == 0 and en_hits == 0:
        return "es"

    return "es" if es_hits >= en_hits else "en"


def clean(text: str, input_source: InputSource = "chat") -> Dict[str, str]:
    """
    Pipeline principal:
    - normalize_text
    - reduce_stt_noise / reduce_ocr_noise según input_source
    - detect_language
    """
    t = normalize_text(text)

    if input_source == "stt":
        t = reduce_stt_noise(t)
    elif input_source == "ocr":
        t = reduce_ocr_noise(t)

    lang = detect_language(t)

    return {"clean_text": t, "language": lang}
