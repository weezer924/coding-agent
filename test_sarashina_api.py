import json
import os

import requests
from dotenv import load_dotenv

# 1. Load the vault
load_dotenv()

sarashina_api_key = os.getenv("SARASHINA_API_KEY")


if not sarashina_api_key:
    print("Error: SARASHINA_API_KEY not found in .env")
    exit(1)

# 2. Define the target
sarashina_url = "https://api.sarashina.ai/v1/chat/completions"


# 3. Authenticate
headers = {
    "Authorization": f"Bearer {sarashina_api_key}",
    "content-type": "application/json",
}

# 4. Construct the payload
payload = {
    "model": "sarashina3-mini",
    "max_completion_tokens": 4096,
    "messages": [{"role": "user", "content": "Sarashinaってどういう意味？"}],
}

# 5. Fire! (No safety net)
print("📡 Sending request to Sarashina...")
response = requests.post(sarashina_url, headers=headers, json=payload, timeout=120)


# 6. Inspect the raw result
print(f"Status: {response.status_code}")

if response.status_code == 200:
    # Success: Print the beautiful JSON
    print("Response:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
else:
    # Failure: Print the ugly raw text so we can debug
    print("Error:", response.text)
