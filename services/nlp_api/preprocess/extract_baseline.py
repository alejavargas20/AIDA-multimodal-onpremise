from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

_MONTHS_ES = (
    "enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre"
)

# Helpers de normalización numérica

def _normalize_number(num_str: str) -> Optional[float]:
    """
    Convierte strings como:
    - "1,200.50" -> 1200.50
    - "1.200,50" -> 1200.50
    - "1200" -> 1200.0
    Heurística: el separador decimal suele ser el último '.' o ','.
    """
    s = num_str.strip()

    # Quitar espacios internos
    s = re.sub(r"\s+", "", s)

    # Si no hay separadores, parse directo
    if "," not in s and "." not in s:
        try:
            return float(s)
        except ValueError:
            return None

    last_dot = s.rfind(".")
    last_comma = s.rfind(",")

    dec_sep = "." if last_dot > last_comma else ","

    # Quitar separadores de miles 
    if dec_sep == ".":
        s = s.replace(",", "")
    else:
        s = s.replace(".", "")

    # Reemplazar separador decimal por '.'
    s = s.replace(dec_sep, ".")

    try:
        return float(s)
    except ValueError:
        return None


# Regex patterns

_DATE_DMY = re.compile(r"\b(0?[1-9]|[12]\d|3[01])[\/\-.](0?[1-9]|1[0-2])[\/\-.](\d{4})\b")
_DATE_YMD = re.compile(r"\b(\d{4})[\/\-.](0?[1-9]|1[0-2])[\/\-.](0?[1-9]|[12]\d|3[01])\b")

# Fechas con mes en texto:
_DATE_MONTH_TEXT = re.compile(
    rf"\b(?:(0?[1-9]|[12]\d|3[01])\s+(?:de\s+)?)?"
    rf"({_MONTHS_ES})\s+(?:de\s+)?(\d{{4}})\b",
    flags=re.IGNORECASE,
)

# Importes:
# soporta USD EUR 
_CURRENCY_PREFIX = r"(?P<prefix>[$€])?"
_CURRENCY_SUFFIX = r"(?P<suffix>(?:USD|EUR|DOLARES|DÓLARES|EUROS))?"
_NUMBER = r"(?P<number>-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?|-?\d+(?:[.,]\d{2})?)"
_AMOUNT = re.compile(
    rf"\b{_CURRENCY_PREFIX}\s*{_NUMBER}\s*{_CURRENCY_SUFFIX}\b",
    flags=re.IGNORECASE,
)

# Porcentajes: 12%, 12.5 %, 12,5 %
_PERCENT = re.compile(r"\b(\d{1,3}(?:[.,]\d+)?)\s*%\b")


# Extracción
def extract_dates(text: str) -> List[str]:
    dates: List[str] = []

    for m in _DATE_DMY.finditer(text):
        dates.append(m.group(0))

    for m in _DATE_YMD.finditer(text):
        dates.append(m.group(0))

    for m in _DATE_MONTH_TEXT.finditer(text):
        # reconstruye la coincidencia completa original
        dates.append(m.group(0))
    return list(dict.fromkeys(dates))


def extract_percentages(text: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in _PERCENT.finditer(text):
        raw = m.group(0)
        num_raw = m.group(1)
        value = _normalize_number(num_raw)
        out.append({"raw": raw, "value": value})
    return list(dict.fromkeys([str(x) for x in out])) and out  


def extract_amounts(text: str) -> List[Dict[str, Any]]:
    amounts: List[Dict[str, Any]] = []

    for m in _AMOUNT.finditer(text):
        raw = m.group(0).strip()
        num_raw = m.group("number")
        prefix = m.group("prefix") or ""
        suffix = (m.group("suffix") or "").upper()

        currency = None
        if prefix == "$":
            currency = "USD"  
        elif prefix == "€":
            currency = "EUR"
        elif suffix:
            currency = suffix

        value = _normalize_number(num_raw)

        amounts.append(
            {
                "raw": raw,
                "currency": currency,
                "value": value,
            }
        )

    # quitar duplicados por raw manteniendo orden
    seen = set()
    unique = []
    for a in amounts:
        key = a["raw"]
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique


def extract_baseline(text: str) -> Dict[str, Any]:
    """
    Devuelve baseline de entidades: fechas, importes, porcentajes.
    """
    return {
        "dates": extract_dates(text),
        "amounts": extract_amounts(text),
        "percentages": extract_percentages(text),
    }
