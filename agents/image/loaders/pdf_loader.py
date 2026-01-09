from typing import List, Any
import fitz  # pymupdf
from PIL import Image
import io

def pdf_to_images_from_path(path: str, max_pages: int) -> List[Any]:
    doc = fitz.open(path)
    images = []
    for i in range(min(len(doc), max_pages)):
        page = doc.load_page(i)
        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        images.append(img)
    return images
