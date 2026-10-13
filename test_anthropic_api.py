import json
import os

import requests
from dotenv import load_dotenv

# 1. Load the vault
load_dotenv()
anthorpic_api_key = os.getenv("ANTHROPIC_API_KEY")


if not anthorpic_api_key:
    print("Error: ANTHROPIC_API_KEY not found in .env")
    exit(1)

# 2. Define the target
anthorpic_url = "https://api.anthropic.com/v1/messages"

# 3. Authenticate
headers = {
    "x-api-key": anthorpic_api_key,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
}

# 4. Construct the payload
payload = {
    "model": "claude-sonnet-5-5",
    "max_tokens": 4096,
    "messages": [{"role": "user", "content": "Hello, are you ready to code?"}],
}

# 5. Fire! (No safety net)
print("📡 Sending request to Claude...")
response = requests.post(anthorpic_url, headers=headers, json=payload, timeout=120)


# 6. Inspect the raw result
print(f"Status: {response.status_code}")

if response.status_code == 200:
    # Success: Print the beautiful JSON
    print("Response:")
    print(json.dumps(response.json(), indent=2))
else:
    # Failure: Print the ugly raw text so we can debug
    print("Error:", response.text)
