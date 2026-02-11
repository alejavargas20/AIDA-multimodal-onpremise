import requests

MCP_URL = "http://localhost:8000/call"

payload = {
    "tool_name": "prompt.optimize",
    "payload": {
        "user_text": "Hazme un resumen de las ventas del mes pasado"
    }
}

response = requests.post(MCP_URL, json=payload)
response.raise_for_status()

print("Respuesta MCP:")
print(response.json())
