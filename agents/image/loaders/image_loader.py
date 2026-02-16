# aida-multimodal-onpremise/agents/image/loaders/image_loader.py

from PIL import Image
import io

def load_image_from_path(path: str) -> Image.Image:
    return Image.open(path).convert("RGB")
