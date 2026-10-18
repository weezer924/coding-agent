import os
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

from tools import tool_definitions


@dataclass
class ToolCall:
    """A tool invocation request from the brain."""

    id: str
    name: str
    args: dict


# text：给人看的文字。可能为空，模型有时只要工具不说话。
# tool_calls：模型要调的工具列表，每项是一个 ToolCall（id、name、args）。空列表就是「答完了」。
# thinking：模型的思考块，有就存，Agent 现在不用。
# raw_content：API 返回的原始 block 列表，原样存进历史用。
class Thought:
    """Standardized response from any Brain. returns 文本、工具调用 or nothing"""

    def __init__(self, text=None, tool_calls=None, thinking=None, raw_content=None):
        self.text = text
        self.tool_calls = tool_calls or []
        self.thinking = thinking
        self.raw_content = raw_content or []


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


class ClaudeBrain(Brain):
    def __init__(self, model="claude-sonnet-5-5", tools=None):
        load_dotenv()
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.headers = {
            "x-api-key": anthorpic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        self.tools = tools or []

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
            raw_content=content,
        )

    def think(self, conversation) -> Thought:
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": conversation,
        }

        if self.tools:
            payload["tools"] = tool_definitions(self.tools)

        resp = requests.post(
            anthorpic_url, headers=self.headers, json=payload, timeout=120
        )

        resp.raise_for_status()
        return self._parse_response(resp.json()["content"])


class SarashinaBrain(Brain):
    def __init__(self, model="sarashina3-mini", tools=None):
        load_dotenv()
        self.api_key = os.getenv("SARASHINA_API_KEY")
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }
        self.tools = tools or []

    def think(self, conversation) -> Thought:
        payload = {
            "model": self.model,
            "messages": conversation,
        }

        if self.tools:
            payload["tools"] = tool_definitions(self.tools)

        resp = requests.post(
            sarashina_url, headers=self.headers, json=payload, timeout=120
        )
        resp.raise_for_status()

        if resp.status_code != 200:
            raise RuntimeError(f"{resp.status_code}: {resp.text[:300]}")

        text = resp.json()["choices"][0]["message"]["content"]
        return Thought(text=text)


BRAINS = {
    "claude": ClaudeBrain,
    "sarashina": SarashinaBrain,  # test expects this key; your second provider
}
