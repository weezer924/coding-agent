from brain import BRAINS
from memory import ToolContext
from tools import get_tool, tool_definitions


class AgentStop(Exception):
    """Raised when the Agent should stop."""


class Agent:
    """A coding agent that processes user input."""

    def __init__(
        self, brain, brain_name: str = "claude", tools=None, memory=None, mode="plan"
    ) -> None:
        self.brain = brain
        self.brain_name = brain_name
        self.conversation = []
        self.tools = tools
        self.context = ToolContext(memory=memory)
        self.memory = memory
        self.mode = mode
        self.brain.tools = self._tools_for_mode()
        self.brain.system = self._build_system_prompt()

    def _build_system_prompt(self):
        """Build system prompt from memory and current mode."""
        parts = [self.memory.content] if self.memory else []
        if self.mode == "plan":
            parts.append(
                "You are in PLAN mode. You cannot write code files. "
                "Use write_plan to save your plans to PLAN.md."
            )
        return "\n".join(parts)

    def _execute_tool(self, tool_name: str, args) -> str:
        tool = get_tool(self.tools, tool_name)

        if tool is None:
            return "not found tool"

        try:
            return tool.execute(self.context, **args)
        except TypeError as e:
            # Missing/extra keys from the model must not kill the loop.
            return f"Error: invalid arguments for {tool_name}: {e}"

    def _tools_for_mode(self):
        if self.mode == "plan":
            result = []
            for t in self.tools:
                if t.name != "write_file":
                    result.append(t)
            return tool_definitions(result)
        else:
            return tool_definitions(self.tools)

    def handle_input(self, user_input: str) -> str:
        text = user_input.strip()

        if not text:
            return ""

        if text == "/q":
            raise AgentStop

        if text == "/switch":
            names = list(BRAINS)
            self.brain_name = names[(names.index(self.brain_name) + 1) % len(names)]
            self.brain = BRAINS[self.brain_name](tools=self.tools, memory=self.memory)
            self.brain.tools = self._tools_for_mode()
            self.brain.system = self._build_system_prompt()
            return f"Switched to {self.brain_name}"

        if text.startswith("/mode"):
            if text == "/mode act":
                self.mode = "act"
                self.brain.tools = self._tools_for_mode()
                self.brain.system = self._build_system_prompt()
                return "Swiched to ACT MODE"
            else:
                self.mode = "plan"
                self.brain.tools = self._tools_for_mode()
                self.brain.system = self._build_system_prompt()
                return "Swiched to PLAN MODE"

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

            ## guardrails for tools
            if not thought.tool_calls:
                break

            ## Tool calls
            tool_call_results = []
            for call in thought.tool_calls:
                if call.raw_args is not None:
                    execute_result = (
                        f"Error: arguments were not valid JSON: {call.raw_args[:200]}"
                    )
                else:
                    execute_result = self._execute_tool(call.name, call.args)
                tool_call_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call.id,
                        "content": execute_result,
                    }
                )

            self.conversation.append({"role": "user", "content": tool_call_results})

        return "\n".join(output)
