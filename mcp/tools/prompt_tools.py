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
  "optimized_prompt": "¿Cuál fue el monto total desembolsado en la última semana?",
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
              "type": "suma",
              "field": None,
              "numerator": None,
              "denominator": None,
              "notes": None
            }
          },
          "entity": {
            "name": "credito",
            "grain": "idSolicitud"
          },
          "data_sources": [
            {
              "table": "desembolso",
              "role": "primary",
              "join_key": None,
              "reason": None
            }
          ],
          "time": {
            "description": None,
            "period": {
              "type": "relative",
              "value": "ultimas_semanas"
            },
            "granularity": None
          },
          "filters": [
            {
              "field": "fecha",
              "operator": ">",
              "value": "now()",
              "table": "desembolso"
            }
          ],
          "comparison": {
            "type": "none",
            "enabled": False
          },
          "scope": {
            "type": "analista",
            "id": None
          },
          "privacy": {
            "allow_sensitive": False,
            "sensitive_fields_detected": []
          },
          "confidence": 1,
          "ambiguities": []
        },
        "params": {}
      }
    ],
    "metadata": {
      "language": "unknown",
      "input_source": "unknown"
    },
    "conductual_state": None,
    "conductual_notes": None
  },
  "status": "ok",
  "errors": []
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
    print("Ha acabado bien el prompt optimizer")
    return resultado


# Registro de la tool en el MCP
TOOL_REGISTRY = {"prompt.optimize": prompt_optimize}
