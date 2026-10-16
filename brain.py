import os
from dataclasses import dataclass

import requests
from dotenv import load_dotenv


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


class Thought:
    def __init__(self, text=None, tool_calls=None, thinking=None):
        self.text = text
        self.tool_calls = tool_calls or []
        self.thinking = thinking


# 1. Load the vault
load_dotenv()
anthorpic_api_key = os.getenv("ANTHROPIC_API_KEY")

# 2. Define the target
anthorpic_url = "https://api.anthropic.com/v1/messages"
sarashina_url = "https://api.sarashina.ai/v1/chat/completions"


class Brain:
    """Base class for LLM providers"""

    def think(self, conversation):
        """Process conversation, return Thought."""
        raise NotImplementedError

    def _parse_response(self, content):
        """Convert API response format to Thought."""
        text_parts = []
        tool_calls = []
        thinking = None

        for block in content:
            if block["type"] == "thinking":
                thinking = block["thinking"]
            elif block["type"] == "text":
                text_parts.append(block["text"])
            elif block["type"] == "tool_use":
                tool_calls.append(
                    ToolCall(id=block["id"], name=block["name"], args=block["input"])
                )

        return Thought(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            thinking=thinking,
        )


class ClaudeBrain(Brain):
    def __init__(self, model="claude-sonnet-5-5"):
        load_dotenv()
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = model
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
        blocks = resp.json()["content"]
        text = "".join(b["text"] for b in blocks if b["type"] == "text")
        thinking = next(
            (b["thinking"] for b in blocks if b["type"] == "thinking"), None
        )
        return Thought(text=text, thinking=thinking)


class SarashinaBrain(Brain):
    def __init__(self, model="sarashina3-mini"):
        load_dotenv()
        self.api_key = os.getenv("SARASHINA_API_KEY")
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }

    def think(self, conversation) -> Thought:
        payload = {
            "model": self.model,
            "messages": conversation,
        }
        resp = requests.post(
            sarashina_url, headers=self.headers, json=payload, timeout=120
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        return Thought(text=text)


BRAINS = {
    "claude": ClaudeBrain,
    "sarashina": SarashinaBrain,  # test expects this key; your second provider
}
