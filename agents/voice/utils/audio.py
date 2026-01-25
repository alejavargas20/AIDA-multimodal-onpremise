from __future__ import annotations

import os
import time
import uuid


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def default_tts_output_path() -> str:
    fname = f"aida_tts_{int(time.time())}_{uuid.uuid4().hex[:8]}.wav"
    return os.path.join(os.getcwd(), "outputs", "voice", fname)
