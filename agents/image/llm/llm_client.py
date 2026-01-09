import json
import requests
from typing import Dict

class LlmClient:

    def __init__(self, endpoint: str, model: str):
        self.endpoint = endpoint
        self.model = model

    def complete_json(self, system_prompt: str, user_prompt: str) -> Dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"}
        }

        response = requests.post(self.endpoint, json=payload)
        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]

        return json.loads(content)
