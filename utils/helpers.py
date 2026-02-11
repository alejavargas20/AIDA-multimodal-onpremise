"""
Utilidades generales.
"""

import json
from typing import Dict

def parse_json_response(raw_response: str) -> Dict:
    raw_response = raw_response.strip()
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        return {
            "relevant_tables": ["desembolso"],
            "relevant_fields": {
                "desembolso": ["idCuenta", "nCosecha", "nMonto", "nPlazo", "dFechaDes", "idSolicitud"]
            },
            "time_field": "nCosecha",
            "reason": "Fallback: asumiendo tabla desembolso y campos típicos de desembolsos"
        }
    
def prepend_declares(sql: str, params: dict) -> str:
    prefix = ""
    if "IdCliente" in params:
        prefix += f"DECLARE @IdCliente INT = {int(params['IdCliente'])};\n"
    return prefix + sql
