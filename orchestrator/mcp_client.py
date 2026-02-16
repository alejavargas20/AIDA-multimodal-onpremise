#orchestator/mcp_client.py

import requests
from mcp.schemas.models import ToolRequest


def call_mcp(tool_name: str, payload: dict) -> dict:
    req = ToolRequest(tool_name=tool_name, payload=payload)

    r = requests.post(
        "http://localhost:8000/call",
        json=req.model_dump(),  # convierte a dict para enviar
        timeout=300,
    )
    r.raise_for_status()
    return r.json()["result"]
