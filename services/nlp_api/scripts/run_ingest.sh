#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."
source .venv/bin/activate

echo "== Running ingest =="
python -m rag.ingest

