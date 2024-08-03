import requests
import json

# Open session to enable streaming
s = requests.Session()
with s.post(
    "https://model-7wlxp82w.api.baseten.co/production/predict",
    headers={"Authorization": "Api-Key QLk2AhIS.ay5p1g5DPDeAcNqveNziEOmh2hW42b6Q"},
    data=json.dumps({
      "prompt": "What even is AGI?",
      "stream": True,
      "max_tokens": 1024
    }),
    # Include stream=True as an argument so the requests libray knows to stream
    stream=True,
) as resp:
    # Print the generated tokens as they get streamed
    for content in resp.iter_content():
        print(content.decode("utf-8"), end="", flush=True)