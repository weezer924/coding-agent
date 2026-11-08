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

    def execute(self, context, path):
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

    def execute(self, context, path, content):
        print(f"  → Writing {path}")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to {path}"
        except Exception as e:
            return f"Error writing file: {e}"


class SaveMemory:
    name = "save_memory"
    description = "Updates your internal memory/scratchpad. Use this to remember user preferences."
    input_schema = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The full text to save.",
            },
        },
        "required": ["content"],
    }

    def execute(self, context, content):
        print("  → Saving memory")
        if context.memory is None:
            return "Error: Memory not available"
        context.memory.save(content)
        return "Memory updated successfully!"


class WritePlan:
    """plan mode restricts the tool set to read-only plus one plan artifact, and the approval gate is the human switching modes”"""

    name = "write_plan"
    description = "Saves a plan to PLAN.md. Use this to outline your approach before making changes."
    input_schema = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The plan content in markdown",
            },
        },
        "required": ["content"],
    }

    def execute(self, context, content):
        print("  → Writing PLAN")
        try:
            with open("PLAN.md", "w", encoding="utf-8") as f:
                f.write(content)
            return "Plan saved"
        except Exception as e:
            return f"Error writing plan: {e}"


tools = [ReadFile(), WriteFile(), SaveMemory(), WritePlan()]


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
