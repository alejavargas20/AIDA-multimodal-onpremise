#from typing import Optional
#from PIL import Image
#import pytesseract

#class OcrEngine:
#    def __init__(self, tesseract_cmd: Optional[str] = None):
#        if tesseract_cmd:
#            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

#    def extract_text_from_image(self, img: Image.Image, language: str = "es") -> str:
#        lang = "spa" if language in ("es", "spa") else language
#        config = "--oem 3 --psm 6"
#        return pytesseract.image_to_string(img, lang=lang, config=config)

from typing import Optional
from PIL import Image
import pytesseract
import numpy as np
import cv2

class OcrEngine:
    def __init__(self, tesseract_cmd: Optional[str] = None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def _preprocess(self, img: Image.Image) -> Image.Image:
        # PIL -> OpenCV (BGR)
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        # 1) Escalar (mejora mucho OCR si la letra es pequeña)
        cv_img = cv2.resize(cv_img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # 2) Gris
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

        # 3) Binarización Otsu
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 4) Sharpen suave
        kernel = np.array([[0, -1, 0],
                           [-1, 5, -1],
                           [0, -1, 0]])
        sharp = cv2.filter2D(th, -1, kernel)

        # OpenCV -> PIL
        return Image.fromarray(sharp)

    def extract_text_from_image(self, img: Image.Image, language: str = "es") -> str:
        lang = "spa" if language in ("es", "spa") else language

        img2 = self._preprocess(img)

        # PSM 6 suele ir bien en bloques de texto.
        # Si te mezcla líneas, prueba psm 4 o 3.
        config = "--oem 3 --psm 6 -c preserve_interword_spaces=1"

        return pytesseract.image_to_string(img2, lang=lang, config=config)
