from typing import Any

def load_image_from_path(path: str) -> Any:
    # Placeholder: aquí meterás PIL/OpenCV luego
    return {"_type": "image", "path": path}

def load_image_from_bytes(b: bytes) -> Any:
    return {"_type": "image", "bytes": True, "size": len(b)}
