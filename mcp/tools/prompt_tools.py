# # Logica Simulada - Agente Prompt Optimizer

# def optimize_prompt(payload: dict) -> dict:
#     """
#     Simula la lógica de reescritura de prompt y generación de JSON de tareas.
#     El 'payload' viene del Orquestador (request.payload).
#     """
#     user_text = payload.get("user_text", "No se encontró texto de usuario.")

#     # Simulacion del resultado del Agente
#     optimized = f"REESCRIBIR Y ADAPTAR: Analiza la intención sobre '{user_text}'."

#     # El JSON de tareas para el Orquestador
#     mock_intent_json = {
#         "intent": "analisis_financiero",
#         "tasks": [
#             {"agent": "data", "action": "consultar", "query": user_text},
#             {"agent": "nlp", "action": "resumir", "input": optimized}
#         ]
#     }

#     return {
#         "optimized_prompt": optimized,
#         "intent_json": mock_intent_json,
#         "status": "mocked_success"
#     }

# # REGISTRO DE LA TOOL
# # Tool_registry que escanea el mcp_server.py
# TOOL_REGISTRY = {
#     # Clave (tool_name)       : Valor (función Python)
#     "prompt.optimize": optimize_prompt,
# }

# print("Prompt tools: optimize_prompt listo para ser registrado.")

# mcp/tools/prompt_optimizer_tools.py

try:
    # Import real (cuando exista)
    from agents.prompt_optimizer.optimizer_logic import process_request
except ImportError:
    # Fallback mock para desarrollo, si el import falla el MCP seguirá funcionando
    def process_request(payload: dict) -> dict:
        return {
            "optimized_prompt": f"OPTIMIZED: {payload.get('user_text', '')}",
            "intent_json": {"intent": "unknown", "tasks": []},
            "status": "mock",
        }


# Tool MCP que llama al Prompt Optimizer
def prompt_optimize(payload: dict) -> dict:
    """
    Tool MCP que llama al Prompt Optimizer.
    El MCP NO sabe como funciona el optimizer.
    Solo pasa el payload y devuelve el resultado.
    """
    # Llama a la función real del agente
    resultado = process_request(payload)
    return resultado


# Registro de la tool en el MCP
TOOL_REGISTRY = {"prompt.optimize": prompt_optimize}
