from typing import TypedDict, Optional, Dict, Any

class AgentPayload(TypedDict, total=False):
    action: str
    intent_path: str
    catalog_path: str
    params: Dict[str, Any]   # ej: {"mode":"table","IdCliente":15675}
