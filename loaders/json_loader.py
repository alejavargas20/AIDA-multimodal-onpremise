"""
Módulo para cargar archivos JSON.
"""

import json

def load_json_file(filename: str) -> str:
    try:
        with open(filename, encoding='utf-8') as f:
            data = json.load(f)
        return json.dumps(data, ensure_ascii=False, indent=None)
    except FileNotFoundError:
        raise ValueError(f"Archivo no encontrado: {filename}")
    except json.JSONDecodeError:
        raise ValueError(f"JSON inválido en: {filename}")