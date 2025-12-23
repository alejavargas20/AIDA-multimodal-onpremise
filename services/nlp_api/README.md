# NLP API (WSL + Ollama en Windows)

## Requisitos
- WSL2 (Ubuntu)
- Python + venv
- Ollama corriendo en Windows (puerto 11434)

## Setup
cd services/nlp_api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

## Run
./scripts/run_ingest.sh
./scripts/run_api.sh

## Test
./scripts/smoke_test.sh
