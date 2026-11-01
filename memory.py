import os


class Memory:
    """Memory all the conversation history"""

    def __init__(
        self,
        path,
    ) -> None:
        self.content = ""
        self.path = path

        if os.path.exists(path=path):
            open(path)
            os.makedirs(dirname, exist_ok=True)

    def save(self, content: str):
        self.content = content


class ToolContext:
    def __init__(
        self,
        memory,
    ) -> None:
        self.memory = memory
