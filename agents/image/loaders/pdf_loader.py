from typing import Any, List

def pdf_to_images_from_path(path: str, max_pages: int) -> List[Any]:
    # Placeholder: sustituir por pypdfium2/pymupdf/pdf2image
    return [{"_type": "pdf_page_image", "path": path, "page": i} for i in range(1, max_pages + 1)]

def pdf_to_images_from_bytes(b: bytes, max_pages: int) -> List[Any]:
    return [{"_type": "pdf_page_image", "bytes": True, "page": i} for i in range(1, max_pages + 1)]
