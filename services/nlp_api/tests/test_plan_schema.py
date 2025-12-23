import json
from schemas.plan_schema import PlannerOutput

def test_example_plan_validates():
    example = {
        "intent": "consulta_datos",
        "confidence": 0.86,
        "tasks": [
            {"agent": "data", "action": "consultar", "input": "Obtener ventas del mes pasado.", "params": {"metric": "ventas", "time_range": "mes_pasado"}},
            {"agent": "nlp", "action": "responder", "input": "Explicar el resultado de ventas del mes pasado.", "params": {"format": "resumen_ejecutivo"}}
        ],
        "metadata": {"language": "es", "input_source": "chat"},
        "conductual_state": None,
        "conductual_notes": None
    }

    validated = PlannerOutput.model_validate(example)
    assert validated.intent.value == "consulta_datos"
    assert len(validated.tasks) >= 1
