from typing import Optional
from PIL import Image
import pytesseract

class OcrEngine:
    def __init__(self, tesseract_cmd: Optional[str] = None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def extract_text_from_image(self, img: Image.Image, language: str = "es") -> str:
        lang = "spa" if language in ("es", "spa") else language
        config = "--oem 3 --psm 6"
        return pytesseract.image_to_string(img, lang=lang, config=config)
