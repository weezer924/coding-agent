import json
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
    # Set only when the provider's arguments string was not valid JSON;
    # args is {} in that case and the raw string is kept for inspection.
    raw_args: str | None = None


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


class RateLimited(RuntimeError):
    """HTTP 429; retry_after is the server's Retry-After in seconds (or None)."""

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


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
                    ToolCall(
                        id=block["id"],
                        name=block["name"],
                        args=block["input"],
                        raw_args=block.get("raw_arguments"),
                    )
                )

        return Thought(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            thinking=thinking,
            raw_content=content,
        )


class ClaudeBrain(Brain):
    def __init__(
        self, model="claude-sonnet-5-5", tools=None, memory=None
    ):  # 推論モデル
        load_dotenv()
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.headers = {
            "x-api-key": anthorpic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        self.tools = tools or []
        self.last_usage = None
        self.memory = memory

    def think(self, conversation) -> Thought:
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": conversation,
        }

        if self.tools:
            payload["tools"] = tool_definitions(self.tools)

        if self.memory:
            payload["system"] = self.memory.content

        resp = requests.post(
            anthorpic_url, headers=self.headers, json=payload, timeout=120
        )

        if resp.status_code != 200:
            raise RuntimeError(f"{resp.status_code}: {resp.text[:300]}")

        body = resp.json()
        self.last_usage = body.get("usage")
        return self._parse_response(body["content"])


class SarashinaBrain(Brain):
    def __init__(
        self,
        model="sarashina3.2-mini-thinking",
        tools=None,
        temperature=None,
        max_completion_tokens=4096,
        memory=None,
    ):
        load_dotenv()
        self.api_key = os.getenv("SARASHINA_API_KEY")
        self.model = model
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens
        self.last_usage = None
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }
        self.tools = tools or []
        self.memory = memory

    def _tool_definitions(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in self.tools
        ]

    def _to_blocks(self, message):
        blocks = []

        if message.get("content"):
            blocks.append({"type": "text", "text": message["content"]})

        for call in message.get("tool_calls") or []:
            raw = call["function"]["arguments"]
            block = {
                "type": "tool_use",
                "id": call["id"],
                "name": call["function"]["name"],
            }
            try:
                block["input"] = json.loads(raw)
            except (json.JSONDecodeError, TypeError) as e:
                # Keep the turn alive: the tool gets {} and reports the bad
                # arguments back to the model instead of the loop crashing.
                block["input"] = {}
                block["raw_arguments"] = raw
                block["parse_error"] = str(e)
            blocks.append(block)
        return blocks

    def _to_messages(self, conversation):
        out = []

        for message in conversation:
            role = message["role"]
            content = message["content"]

            if isinstance(content, str):
                out.append(message)
            elif role == "assistant":
                texts = []
                calls = []

                for block in content:
                    if block["type"] == "text":
                        texts.append(block["text"])
                    elif block["type"] == "tool_use":
                        calls.append(
                            {
                                "id": block["id"],
                                "type": "function",
                                "function": {
                                    "name": block["name"],
                                    "arguments": json.dumps(block["input"]),
                                },
                            }
                        )
                new_msg = {"role": "assistant", "content": "\n".join(texts)}
                if calls:
                    new_msg["tool_calls"] = calls
                out.append(new_msg)
            else:
                for block in content:
                    out.append(
                        {
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": block["content"],
                        }
                    )
        return out

    def think(self, conversation) -> Thought:
        messages = self._to_messages(conversation)
        if self.memory:
            # insert(0, x) 是「放到第 0 位」，后面的整体后移。OpenAI 风格要求 system 消息是第一条。
            messages.insert(0, {"role": "system", "content": self.memory.content})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": self.max_completion_tokens,
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature

        if self.tools:
            payload["tools"] = self._tool_definitions()
            payload["tool_choice"] = "auto"

        resp = requests.post(
            sarashina_url, headers=self.headers, json=payload, timeout=120
        )

        if resp.status_code == 429:
            ra = resp.headers.get("Retry-After")
            raise RateLimited(f"429: {resp.text[:300]}", float(ra) if ra else None)
        if resp.status_code != 200:
            raise RuntimeError(f"{resp.status_code}: {resp.text[:300]}")

        body = resp.json()
        self.last_usage = body.get("usage")
        message = body["choices"][0]["message"]
        return self._parse_response(self._to_blocks(message))


BRAINS = {
    "claude": ClaudeBrain,
    "sarashina": SarashinaBrain,
}
