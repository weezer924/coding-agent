class AgentStop(Exception):
    """Agent stop."""


class Agent:
    def __init__(self, brain) -> None:
        self.brain = brain
        self.conversation = []

    def handle_input(self, user_input: str) -> str:
        input = user_input.strip()

        if not input:
            return ""

        if input == "/q":
            raise AgentStop

        self.conversation.append({"role": "user", "content": input})

        try:
            thought = self.brain.think(self.conversation)
        except Exception as e:
            self.conversation.pop()
            return f"Error: {e}"
        self.conversation.append({"role": "assistant", "content": thought.text})
        return thought.text
