# aida-multimodal-onpremise/mcp/tools/data_tools.py
import sys
import os
import traceback
import warnings

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))

if root_dir not in sys.path:
    sys.path.append(root_dir)

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
        print(f"🚨 ERROR FATAL AL EJECUTAR DATA AGENT 🚨")
        traceback.print_exc()
        print("="*50 + "\n")
        return {
            "status": "error",
            "error": f"Crash del servidor: {e}"
        }

TOOL_REGISTRY = {
    "data.process": data_process
}