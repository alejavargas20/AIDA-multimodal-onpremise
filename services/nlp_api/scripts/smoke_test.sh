#!/usr/bin/env bash
set -e

API_URL="${API_URL:-http://localhost:8000/nlp/answer}"

echo "== Smoke test: $API_URL =="

# Enviamos retrieval=false para que sea rápido/estable, y no depender de Chroma
RESP=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{"question":"Dime en una frase qué es AIDA.","history":[],"retrieval":false,"top_k":4,"input_source":"chat","language":"es"}')

# Validación mínima: que sea JSON y contenga la clave "answer"
echo "$RESP" | jq -e '.answer' >/dev/null

echo "OK Respuesta contiene 'answer'"
echo "$RESP" | jq
