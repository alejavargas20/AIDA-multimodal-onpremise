#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."
source .venv/bin/activate

WIN_HOST=$(grep -m1 nameserver /etc/resolv.conf | awk '{print $2}')
export OLLAMA_BASE_URL="http://$WIN_HOST:11434"
export MODEL_NAME="${MODEL_NAME:-llama3.2:3b}"

echo "== Checking Ollama at $OLLAMA_BASE_URL =="
if ! curl -sSf "$OLLAMA_BASE_URL/api/version" >/dev/null; then
  echo "ERROR: Ollama no responde en $OLLAMA_BASE_URL"
  echo "Abre Ollama en Windows (tray) y vuelve a ejecutar."
  exit 1
fi

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000


