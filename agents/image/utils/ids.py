import hashlib
from agents.image.schemas.image_models import ImageAgentRequest

def stable_content_id(req: ImageAgentRequest) -> str:
    h = hashlib.sha256()
    h.update(req.input_type.encode("utf-8"))
    if req.path:
        h.update(req.path.encode("utf-8"))
    if req.content_bytes:
        h.update(req.content_bytes[:1024])
    h.update(req.user_prompt.encode("utf-8"))
    return h.hexdigest()[:16]
