# aida-multimodal-onpremise/mcp/tools/data_tools.py
import sys
import os
import traceback
import warnings

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
try:
    warnings.filterwarnings('ignore', category=UserWarning, module='pandas')
    from agents.data.data_logic import process
    print("[MCP] DATA Agent cargado correctamente.")
except Exception as e:
    print(f"[MCP] Error fatal al cargar DATA Agent:")
    traceback.print_exc()
    def process(payload: dict) -> dict:
        return {
            "status": "error",
            "error": f"Data Agent no disponible. Error de carga: {e}",
            "sql": "",
            "execution_result": []
        }

def data_process(payload: dict) -> dict:
    try:
        return process(payload)
    except Exception as e:
        print("\n" + "="*50)
        print(f"ERROR FATAL AL EJECUTAR DATA AGENT")
        traceback.print_exc()
        print("="*50 + "\n")
        return {
            "status": "error",
            "error": f"Crash del servidor: {e}"
        }

TOOL_REGISTRY = {
    "data.process": data_process
}