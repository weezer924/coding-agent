from brain import BRAINS
from tools import get_tool


class AgentStop(Exception):
    """Raised when the Agent should stop."""


class Agent:
    """A coding agent that processes user input."""

    def __init__(self, brain, brain_name: str = "claude", tools=None) -> None:
        self.brain = brain
        self.brain_name = brain_name
        self.conversation = []
        self.tools = tools

    def _execute_tool(self, tool_name: str, args) -> str:
        tool = get_tool(self.tools, tool_name)

        if tool is None:
            return "not found tool"

        return tool.execute(**args)

    def handle_input(self, user_input: str) -> str:
        text = user_input.strip()

        if not text:
            return ""

        if text == "/q":
            raise AgentStop

        if text == "/switch":
            names = list(BRAINS)
            self.brain_name = names[(names.index(self.brain_name) + 1) % len(names)]
            self.brain = BRAINS[self.brain_name](tools=self.tools)
            return f"Switched to {self.brain_name}"

        start = len(self.conversation)
        self.conversation.append({"role": "user", "content": text})

        output = []
        for _ in range(20):
            try:
                thought = self.brain.think(self.conversation)
            except Exception as e:
                self.conversation = self.conversation[:start]
                return f"Error: {e}"

            self.conversation.append(
                {"role": "assistant", "content": thought.raw_content}
            )
            if thought.text:
                output.append(thought.text)

            if not thought.tool_calls:
                break

            results = []
            for call in thought.tool_calls:
                result = self._execute_tool(call.name, call.args)
                results.append(
                    {"type": "tool_result", "tool_use_id": call.id, "content": result}
                )
            self.conversation.append({"role": "user", "content": results})

        return "\n".join(output)
