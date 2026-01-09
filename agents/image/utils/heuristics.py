def guess_doc_type(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in ["factura", "invoice", "subtotal", "iva", "total"]):
        return "invoice_like"
    if any(k in t for k in ["dni", "pasaporte", "nif", "documento nacional"]):
        return "id_document_like"
    if any(k in t for k in ["contrato", "cláusula", "acuerdo", "partes"]):
        return "contract_like"
    if len(t) < 80:
        return "short_text"
    return "unknown"

def basic_text_quality_metrics(text: str) -> dict:
    if not text:
        return {"char_count": 0, "alnum_ratio": 0.0, "line_count": 0}
    char_count = len(text)
    alnum = sum(c.isalnum() for c in text)
    alnum_ratio = alnum / max(1, char_count)
    line_count = text.count("\n") + 1
    return {"char_count": char_count, "alnum_ratio": round(alnum_ratio, 3), "line_count": line_count}
