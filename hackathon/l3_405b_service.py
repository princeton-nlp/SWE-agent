import requests
import json
import os

# Send request without streaming
API_KEY = os.getenv("BASETEN_API_KEY")
response = requests.post(
    "https://model-7wlxp82w.api.baseten.co/production/predict",
    headers={"Authorization": f"Api-Key {API_KEY}"},
    json={
        "prompt": "What even is AGI?",
        "stream": False,
        "max_tokens": 500
    }
)

# Get the full response
if response.status_code == 200:
    result = response.json()
    print(result)
else:
    print(f"Error: {response.status_code}")
    print(response.text)