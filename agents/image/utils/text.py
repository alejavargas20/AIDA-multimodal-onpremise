from __future__ import annotations
import re
import unicodedata
from typing import Iterable, Optional

# ----------------------------
# 1) Normalización base
# ----------------------------
_whitespace_re = re.compile(r"[ \t]+")
_newlines_re = re.compile(r"\n{3,}")

def normalize_text(text: str) -> str:
    """Limpieza segura (no cambia palabras, solo formato)."""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = _whitespace_re.sub(" ", text)
    text = _newlines_re.sub("\n\n", text)
    return text.strip()

# ----------------------------
# 2) Separar palabras pegadas
# ----------------------------
# "Fechade" -> "Fecha de", "Montodel" -> "Monto del"
_JOINED_PREP = re.compile(
    r"\b([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,})(de|del|la|el|los|las)\b",
    re.IGNORECASE
)

# "MesMarzo2024" -> "Mes Marzo 2024" (letra->mayúscula, letra->número, número->letra)
_CAMEL = re.compile(r"([a-záéíóúüñ])([A-ZÁÉÍÓÚÜÑ])")
_LETTER_NUM = re.compile(r"([A-Za-zÁÉÍÓÚÜÑáéíóúüñ])(\d)")
_NUM_LETTER = re.compile(r"(\d)([A-Za-zÁÉÍÓÚÜÑáéíóúüñ])")

def split_joined_tokens(text: str) -> str:
    text = _JOINED_PREP.sub(r"\1 \2", text)
    text = _CAMEL.sub(r"\1 \2", text)
    text = _LETTER_NUM.sub(r"\1 \2", text)
    text = _NUM_LETTER.sub(r"\1 \2", text)
    return text


# ----------------------------
# 3) Normalización de puntuación y separadores
# ----------------------------
# Arregla casos típicos:
# "3 600.000" -> "3.600.000" (si parece miles)
# "29,100" -> "29.100" (si parece miles, no decimal)
_thousands_space = re.compile(r"\b(\d{1,3})\s(\d{3}\b)")
_thousands_commas = re.compile(r"\b(\d{1,3}),(\d{3}\b)")

def normalize_numbers(text: str) -> str:
    text = _thousands_space.sub(r"\1.\2", text)
    text = _thousands_commas.sub(r"\1.\2", text)
    return text


# ----------------------------
# 4) Corrección por léxico + fuzzy (opcional)
# ----------------------------
def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

def _token_key(tok: str) -> str:
    tok = tok.strip(".,;:()[]{}\"'¡!¿?").strip()
    tok = _strip_accents(tok.lower())
    return tok

def correct_by_lexicon(
    text: str,
    lexicon: Iterable[str],
    threshold: int = 90,
    min_len: int = 6
) -> str:
    """
    Corrige tokens que se parecen MUCHO a términos del dominio (sin inventar contenido).
    Requiere rapidfuzz. Si no está, no hace nada.
    """
    try:
        from rapidfuzz import process as fuzz_process, fuzz
    except Exception:
        return text

    # Prepara lexicon normalizado -> original
    lex_map = {}
    for w in lexicon:
        lex_map[_token_key(w)] = w

    lex_keys = list(lex_map.keys())

    def preserve_case(src: str, repl: str) -> str:
        if src.isupper():
            return repl.upper()
        if src[:1].isupper():
            return repl[:1].upper() + repl[1:]
        return repl

    out_tokens = []
    for tok in text.split():
        key = _token_key(tok)

        # No tocar números puros / fechas / monedas evidentes
        if not key or key.isdigit() or any(ch.isdigit() for ch in key) and ("/" in tok or ":" in tok):
            out_tokens.append(tok)
            continue

        if len(key) < min_len:
            out_tokens.append(tok)
            continue

        if key in lex_map:
            out_tokens.append(tok)  # ya está bien
            continue

        match_key, score, _ = fuzz_process.extractOne(key, lex_keys, scorer=fuzz.WRatio)
        if score >= threshold:
            repl = lex_map[match_key]
            out_tokens.append(preserve_case(tok, repl))
        else:
            out_tokens.append(tok)

    return " ".join(out_tokens)


# ----------------------------
# 5) Pipeline final
# ----------------------------
DEFAULT_FINANCE_LEXICON = [
    # Cabeceras típicas
    "Reporte", "Desembolsos", "Último", "Mes", "Mes analizado", "Región", "Nacional",
    "Total", "Créditos", "Crédito", "Desembolsados",
    "Monto", "Monto total", "Promedio", "Producto", "Por", "Plazo", "Meses",
    "Clientes", "Nuevos", "Concedido", "Concesión",
    "Administración", "Concedente", "Ayuntamiento", "Madrid",
    # Meses
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
    "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

def postprocess_ocr_text(
    raw_text: str,
    lexicon: Optional[Iterable[str]] = None
) -> str:
    if lexicon is None:
        lexicon = DEFAULT_FINANCE_LEXICON

    # 1) Normalización básica (respeta \n)
    text = normalize_text(raw_text)

    # 2) Procesar por líneas para no perder estructura
    lines = text.split("\n")
    processed_lines = []

    for line in lines:
        if not line.strip():
            processed_lines.append("")  # línea en blanco
            continue

        line = split_joined_tokens(line)
        line = normalize_numbers(line)
        line = correct_by_lexicon(line, lexicon=lexicon, threshold=90, min_len=6)
        processed_lines.append(line)

    # 3) Reconstruir el texto respetando saltos
    text = "\n".join(processed_lines)

    # 4) Normalización final ligera (sin colapsar \n)
    text = normalize_text(text)

    return text
