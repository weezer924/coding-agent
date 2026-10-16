from brain import BRAINS


class AgentStop(Exception):
    """Agent stop."""


class Agent:
    def __init__(self, brain, brain_name: str = "claude") -> None:
        self.brain = brain
        self.brain_name = brain_name
        self.conversation = []

    def handle_input(self, user_input: str) -> str:
        input = user_input.strip()

        if not input:
            return ""

        if input == "/q":
            raise AgentStop

        if input == "/switch":
            names = list(BRAINS)
            self.brain_name = names[(names.index(self.brain_name) + 1) % len(names)]
            self.brain = BRAINS[self.brain_name]()
            return f"Switched to {self.brain_name}"

        self.conversation.append({"role": "user", "content": input})

        try:
            thought = self.brain.think(self.conversation)
        except Exception as e:
            self.conversation.pop()
            return f"Error: {e}"

        self.conversation.append({"role": "assistant", "content": thought.text})

        return thought.text
