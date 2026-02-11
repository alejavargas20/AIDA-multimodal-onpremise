# Logica Simulada - Agente Prompt Optimizer


def optimize_prompt(payload: dict) -> dict:
    """
    Simula la lógica de reescritura de prompt y generación de JSON de tareas.
    El 'payload' viene del Orquestador (request.payload).
    """
    user_text = payload.get("user_text")

    # Simulacion del resultado del Agente
    optimized = f"{user_text}"

    # El JSON de tareas para el Orquestador
    mock_intent_json = {
        "optimized_prompt": "Muéstrate el monto promedio desembolsado por mes, de los últimos 6 meses",
        "intent_plan": {
            "intent": "analitica_desembolsos",
            "confidence": 0.9,
            "tasks": [
                {
                    "agent": "data",
                    "action": "fetch_metrics",
                    "input": {
                        "metric": {
                            "concept": "monto_desembolsado",
                            "description": None,
                            "aggregation": {
                                "type": "avg",
                                "field": "monto",
                                "notes": None,
                            },
                        },
                        "entity": {"name": "credito", "grain": "idCuenta"},
                        "data_sources": [
                            {"table": "desembolso", "role": "primary", "reason": None}
                        ],
                        "time": {
                            "description": None,
                            "period": {"type": "relative", "value": "ultimo_6_meses"},
                            "granularity": "mensual",
                        },
                        "filters": [],
                        "comparison": {"type": "none", "enabled": False},
                        "scope": {"type": "analista", "id": None},
                        "privacy": {
                            "allow_sensitive": False,
                            "sensitive_fields_detected": ["idCuenta"],
                        },
                        "confidence": 1.0,
                        "ambiguities": [],
                    },
                    "params": {},
                }
            ],
            "metadata": {"language": "es", "input_source": "unknown"},
            "conductual_state": None,
            "conductual_notes": None,
        },
        "status": "ok",
        "errors": [],
    }

    print(mock_intent_json)

    return mock_intent_json


# Tool MCP que llama al Prompt Optimizer
def prompt_optimize(payload: dict) -> dict:
    """
    Tool MCP que llama al Prompt Optimizer.
    El MCP NO sabe como funciona el optimizer.
    Solo pasa el payload y devuelve el resultado.
    """
    # Llama a la función real del agente
    resultado = optimize_prompt(payload)
    print(resultado)
    return resultado


# Registro de la tool en el MCP
TOOL_REGISTRY = {"prompt.optimize": prompt_optimize}
