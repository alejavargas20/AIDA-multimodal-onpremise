import os
from pathlib import Path

import rag.ingest as ingest_mod


class DummyEmbeddings:
    """Embeddings fake para que NO descargue modelos."""
    def embed_documents(self, texts):
        return [[0.0] * 8 for _ in texts]

    def embed_query(self, text):
        return [0.0] * 8


def test_ingest_indexes_chunks(tmp_path, monkeypatch, capsys):
    """
    Test mínimo de ingesta:
    - crea un txt de prueba
    - ejecuta ingest()
    - verifica que crea carpeta chroma y que imprime OK: N chunks...
    - sin depender de HuggingFace (parchea embeddings)
    """

    raw_dir = tmp_path / "raw"
    chroma_dir = tmp_path / "chroma"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # TXT largo para forzar >1 chunk 
    demo = raw_dir / "demo.txt"
    demo.write_text(("AIDA crédito personal. " * 2000), encoding="utf-8")

    # Ajusta dirs en el módulo 
    ingest_mod.RAW_DIR = str(raw_dir)
    ingest_mod.CHROMA_DIR = str(chroma_dir)

    # Parchea embeddings para evitar descargas
    monkeypatch.setattr(ingest_mod, "HuggingFaceEmbeddings", lambda model_name=None: DummyEmbeddings())

    # Ejecuta ingesta
    ingest_mod.ingest()

    out = capsys.readouterr().out
    assert "OK:" in out
    assert "chunks indexados" in out

    # Verifica que la carpeta de chroma existe 
    assert Path(ingest_mod.CHROMA_DIR).exists()
    assert any(Path(ingest_mod.CHROMA_DIR).iterdir())
