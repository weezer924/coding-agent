import os


class Memory:
    """Memory all the conversation history"""

    def __init__(
        self,
        path,
    ) -> None:
        self.content = ""
        self.path = path

        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        if os.path.exists(path):
            with open(path) as f:
                self.content = f.read()
        else:
            self.save("Nanocode")

    def save(self, content: str):
        self.content = content
        with open(self.path, "w") as f:
            f.write(content)


class ToolContext:
    def __init__(
        self,
        memory=None,
    ) -> None:
        self.memory = memory
