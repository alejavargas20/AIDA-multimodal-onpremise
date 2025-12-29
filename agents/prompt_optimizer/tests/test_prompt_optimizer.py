import json
from agents.prompt_optimizer import process_request


def test_process_request_returns_dict():
    payload = {
        "user_text": "Hazme un resumen del comportamiento de la cartera el último trimestre",
        "history": [],
        "metadata": {"language": "es", "input_source": "chat"},
        "constraints": {"output_format": "json_only", "max_tasks": 3},
    }
    out = process_request(payload)
    assert isinstance(out, dict)


def test_output_is_json_serializable():
    payload = {
        "user_text": "Analiza riesgo de mora y dame KPIs agregados",
        "history": [],
        "metadata": {"language": "es", "input_source": "chat"},
        "constraints": {"output_format": "json_only", "max_tasks": 3},
    }
    out = process_request(payload)
    json.dumps(out)


def test_minimal_contract_present():
    payload = {
        "user_text": "Necesito KPIs de cartera por trimestre",
        "metadata": {"language": "es", "input_source": "chat"},
    }
    out = process_request(payload)
    assert "intent_plan" in out
    assert "intent" in out["intent_plan"]
    assert "tasks" in out["intent_plan"]


def test_tasks_limit():
    payload = {
        "user_text": "Resume este documento",
        "metadata": {"language": "es", "input_source": "ocr"},
        "constraints": {"max_tasks": 3},
    }
    out = process_request(payload)
    assert len(out["intent_plan"]["tasks"]) <= 3


def test_no_sql_in_tasks():
    payload = {
        "user_text": "Quiero un SELECT * FROM tabla",
        "metadata": {"language": "es", "input_source": "chat"},
    }
    out = process_request(payload)
    # Should never leak SQL into Task.input
    for t in out["intent_plan"]["tasks"]:
        assert "select " not in t["input"].lower()
        assert " from " not in t["input"].lower()
