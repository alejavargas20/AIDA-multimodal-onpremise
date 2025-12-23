from agents.nlp.nlp_logic import process


def test_process_respond_structure():
    payload = {
        "task": "respond",
        "input": {"text": "Hola, prueba." , "retrieval": False},
        "metadata": {"language": "es", "input_source": "chat"},
    }
    out = process(payload)
    assert out["ok"] is True
    assert out["task"] == "respond"
    assert "text" in out["result"]


def test_process_invalid_task():
    payload = {
        "task": "no_existe",
        "input": {"text": "hola"},
        "metadata": {"language": "es", "input_source": "chat"},
    }
    out = process(payload)
    assert out["ok"] is False
    assert "error" in out

