from typing import Any, Dict, List

class LayoutLMv3Extractor:
    def __init__(self, model_name: str = "microsoft/layoutlmv3-base"):
        self.model_name = model_name
        # Aquí cargarías processor/model cuando lo tengáis listo.

    def extract(self, image: Any, text: str) -> Dict[str, Any]:
        # Placeholder: devolver estructura dummy
        return {"doc_type": "unknown", "key_points": [], "entities": []}
