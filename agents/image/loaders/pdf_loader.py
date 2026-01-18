from typing import List
import pypdfium2 as pdfium
from PIL import Image

def pdf_to_images_from_path(path: str, max_pages: int = 10, dpi: int = 200) -> List[Image.Image]:
    pdf = pdfium.PdfDocument(path)
    n_pages = min(len(pdf), max_pages)
    images: List[Image.Image] = []
    for i in range(n_pages):
        page = pdf[i]
        bitmap = page.render(scale=dpi / 72)
        images.append(bitmap.to_pil().convert("RGB"))
    return images
