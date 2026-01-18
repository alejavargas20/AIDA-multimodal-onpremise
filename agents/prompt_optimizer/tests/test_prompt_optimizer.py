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
        inp = t["input"]
        as_text = inp if isinstance(inp, str) else json.dumps(inp, ensure_ascii=False)
        assert "select " not in as_text.lower()
        assert " from " not in as_text.lower()


def test_data_action_is_fetch_metrics_for_financial_intents():
    payload = {
        "user_text": "Analiza riesgo agregado de la cartera y dame KPIs del último mes",
        "metadata": {"language": "es", "input_source": "chat"},
    }
    out = process_request(payload)
    tasks = out["intent_plan"]["tasks"]

    if tasks and tasks[0]["agent"] == "data":
        assert tasks[0]["action"] == "fetch_metrics"

def test_baseline_nlp_input_is_dict_when_llm_disabled(monkeypatch):
    monkeypatch.setenv("USE_LLM_PLANNER", "false")

    payload = {
        "user_text": "Hazme un resumen de las ventas del mes pasado",
        "metadata": {"language": "es", "input_source": "chat"},
    }

    out = process_request(payload)
    tasks = out["intent_plan"]["tasks"]
    assert isinstance(tasks, list) and len(tasks) == 1
    assert tasks[0]["agent"] == "nlp"
    assert isinstance(tasks[0]["input"], dict)
    assert "text" in tasks[0]["input"]