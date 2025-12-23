from fastapi.testclient import TestClient
import app.main as main


def test_nlp_answer_endpoint_shape(monkeypatch):
    """
    Test mínimo del endpoint:
    - Responde 200
    - Devuelve JSON con las claves esperadas
    - Sin depender de Ollama (mock de answer_with_rag)
    """

    def fake_answer_with_rag(question, history, retrieval, top_k):
        return (
            "respuesta dummy",
            [],          # used_docs
            12           # elapsed_ms
        )

    monkeypatch.setattr(main, "answer_with_rag", fake_answer_with_rag)

    client = TestClient(main.app)

    payload = {
        "question": "test",
        "history": [],
        "retrieval": False,
        "top_k": 4,
        "input_source": "chat",
        "language": "es",
    }

    r = client.post("/nlp/answer", json=payload)
    assert r.status_code == 200

    data = r.json()
    assert "answer" in data
    assert "used_docs" in data
    assert "metadata" in data
    assert "conductual_state" in data
    assert "conductual_notes" in data

    # Tipos básicos
    assert isinstance(data["answer"], str)
    assert isinstance(data["used_docs"], list)
    assert isinstance(data["metadata"], dict)
