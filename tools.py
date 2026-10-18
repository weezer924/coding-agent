class ReadFile:
    name = "read_file"
    description = "Read a file and return its contents with line numbers."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file"},
        },
        "required": ["path"],
    }

    def execute(self, path):
        try:
            with open(path) as f:
                lines = f.readlines()
        except Exception as e:
            return f"Error: {e}"
        return "".join(f"{i} | {line}" for i, line in enumerate(lines, 1))


class WriteFile:
    name = "write_file"
    description = "Writes content to a file. OVERWRITES existing content."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file"},
            "content": {
                "type": "string",
                "description": "The full content to write",
            },
        },
        "required": ["path", "content"],
    }

    def execute(self, path, content):
        print(f"  → Writing {path}")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to {path}"
        except Exception as e:
            return f"Error writing file: {e}"


tools = [ReadFile(), WriteFile()]


def get_tool(tools, name):
    for tool in tools:
        if tool.name == name:
            return tool
    return None


def tool_definitions(tools):
    return [
        {"name": t.name, "description": t.description, "input_schema": t.input_schema}
        for t in tools
    ]
