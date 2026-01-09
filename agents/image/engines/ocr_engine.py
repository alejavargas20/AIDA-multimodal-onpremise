from typing import Any, Optional
import pytesseract

class OcrEngine:
    def __init__(self, tesseract_cmd: Optional[str] = None):
        # Si no está en PATH, pásalo:
        # r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def extract_text_from_image(self, image_obj: Any, language_hint: Optional[str] = None) -> str:
        lang = "spa" if (language_hint in (None, "es", "spa")) else language_hint
        config = "--oem 3 --psm 6"
        return pytesseract.image_to_string(image_obj, lang=lang, config=config)
