from PIL import Image
import io

def load_image_from_path(path: str) -> Image.Image:
    return Image.open(path).convert("RGB")

def load_image_from_bytes(b: bytes) -> Image.Image:
    return Image.open(io.BytesIO(b)).convert("RGB")
