from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import importlib
import os
import importlib.util
import uvicorn
from typing import Dict, Callable


# Crear la instancia de FastAPI
app = FastAPI(
    title="AIDA - Model Context Protocol (MCP) Server",
    description="Capa de Herramientas Estandarizadas para Agentes de IA On-Premise.",
)


# Estructura basica para requests del orquestador
class ToolRequest(BaseModel):
    tool_name: str
    payload: dict


# Registro de herramientas
TOOLS: Dict[str, Callable] = {}


# Funcion de escaneo
def load_tools(tools_dir="mcp/tools"):
    """
    Escanea la carpeta de tools y registra las funciones encontradas
    en el diccionario TOOLS.
    Cada archivo debe definir TOOL_REGISTRY.

    """
    print(f"Buscando tools en {tools_dir}...")

    # Iterar sobre todos los archivos de la carpeta
    for filename in os.listdir(tools_dir):
        # Solo procesar archivos Python y no __init__.py
        if filename.endswith("_tools.py"):
            module_path = os.path.join(tools_dir, filename)
            module_name = filename[:-3]  # Quitar .py

            # importacion dinamica
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Buscar la variable 'TOOL_REGISTRY' dentro del modulo cargado
            if hasattr(module, "TOOL_REGISTRY"):
                TOOLS.update(module.TOOL_REGISTRY)


# Llamar a la funcion antes de arrancar el servidor
load_tools()


# Health check endpoint
@app.get("/health")
def health():
    return {"status": "ok", "tools_loaded": list(TOOLS.keys())}


# Listar herramientas disponibles
@app.get("/tools")
def list_tools():
    return {"tools": list(TOOLS.keys())}


# MAIN MCP ENDPOINT


# Endpoint orquestador
@app.post("/call")
def call_tool(request: ToolRequest):
    tool = TOOLS.get(request.tool_name)  # busca la tool

    if not tool:
        raise HTTPException(
            status_code=404, detail=f"Tool '{request.tool_name}' not found"
        )

    # Llama al agente
    try:
        result = tool(request.payload)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ENTRYPOINT

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
