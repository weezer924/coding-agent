import os
from dataclasses import dataclass, field

import requests
from dotenv import load_dotenv


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class Thought:
    text: str
    tool_calls: list = field(default_factory=list)
    thinking: str | None = None


# 1. Load the vault
load_dotenv()
anthorpic_api_key = os.getenv("ANTHROPIC_API_KEY")

# 2. Define the target
anthorpic_url = "https://api.anthropic.com/v1/messages"


class ClaudeBrain:
    def __init__(self, model="claude-sonnet-5-5"):
        load_dotenv()
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.responses = []
        # 3. Authenticate
        self.headers = {
            "x-api-key": anthorpic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def think(self, conversation) -> Thought:
        payload = {"model": self.model, "max_tokens": 4096, "messages": conversation}
        resp = requests.post(
            anthorpic_url, headers=self.headers, json=payload, timeout=120
        )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"]
        return Thought(text=text)
