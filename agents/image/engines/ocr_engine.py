from typing import Any, Optional

class OcrEngine:

    def __init__(self):
        from paddleocr import PaddleOCR
        self.ocr = PaddleOCR(
            lang="es",
            use_angle_cls=False,
            use_gpu=False
        )

    def extract_text_from_image(
        self,
        image_obj: Any,
        language_hint: Optional[str] = None
    ) -> str:
        """
        Extrae texto OCR y lo devuelve como un string único.
        """

        # image_obj aquí ya debería ser una imagen real (numpy / PIL)
        result = self.ocr.ocr(image_obj, cls=False)

        lines = []

        for block in result:
            for line in block:
                text = line[1][0]
                if text:
                    lines.append(text)

        return "\n".join(lines)
