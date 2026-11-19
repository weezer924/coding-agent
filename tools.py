import os
import subprocess

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "node_modules",
}


class ReadFile:
    name = "read_file"
    plan_safe = True
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
    plan_safe = False
    description = "Create a new file or completely overwrite an existing one with the given content. For small changes to an existing file, use edit_file instead."
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
            return "Successfully wrote"
        except Exception as e:
            return f"Error writing file: {e}"


class ListFiles:
    """Lists files in the project structure."""

    name = "list_files"
    plan_safe = True
    description = "List all the files under the path. Use this first to understand the project structure"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "The root path (default '.')"},
        },
    }

    def execute(self, context, path="."):
        try:
            file_list = []
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

                level = root.replace(path, "").count(os.sep)
                indent = " " * 4 * (level)
                file_list.append(f"{indent}{os.path.basename(root)}/")
                subindent = " " * 4 * (level + 1)
                for f in files:
                    file_list.append(f"{subindent}{f}")

            return "\n".join(file_list)
        except Exception as e:
            return f"Error look up Path: {e}"


class SearchCodebase:
    """Searches for a string in all files."""

    name = "search_codebase"
    plan_safe = True
    description = "Searches the entire codebase for a text string. Useful to find where functions or variables are defined."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The string to search for"},
            "path": {"type": "string", "description": "The root path (default '.')"},
        },
    }

    def execute(self, context, query, path="."):
        print(f"  → Searching for '{query}'")
        results = []
        try:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        with open(
                            file_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            for i, line in enumerate(f):
                                if query.lower() in line.lower():
                                    results.append(
                                        f"{file_path}:{i + 1}: {line.strip()}"
                                    )
                    except Exception:
                        continue

            return "\n".join(results) if results else "No matches found."
        except Exception as e:
            return f"Error search codebase {e}"


class SaveMemory:
    name = "save_memory"
    plan_safe = False
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
    plan_safe = True
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


class RunCommand:
    """Executes shell commands."""

    name = "run_command"
    plan_safe = False
    description = "Executes a terminal command. Use this to run scripts, tests, or install packages."
    input_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to run, e.g. 'pytest -q' or 'ls src'",
            },
        },
        "required": ["command"],
    }

    def execute(self, context, command):
        print(f"  → Runing: {command[:50]}")
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )

            stdout = result.stdout[:5000]
            stderr = result.stderr[:5000]

            return f"STDOUT: \n {stdout} \n\nSTDERR:\n {stderr} \n\nExit code: {result.returncode}"
        except subprocess.TimeoutExpired:
            return "Error: command timed out after 30 seconds"
        except Exception as e:
            return f"Error executing command: {e}"


class EditFile:
    """Replaces text in a file (surgical edit)."""

    name = "edit_file"
    plan_safe = False
    description = "Replace one exact occurrence of old_text with new_text in a file. "
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file",
            },
            "new_text": {
                "type": "string",
                "description": "Text to replace it with",
            },
            "old_text": {
                "type": "string",
                "description": "Exact text to find and replace",
            },
        },
        "required": ["path", "new_text", "old_text"],
    }

    def execute(self, context, path, old_text, new_text):
        print(f"  → Editing {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if old_text not in content:
                return f"Error: Could not find the specified text in {path}"
            new_content = content.replace(old_text, new_text, 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"Successfully edited {path}"
        except Exception as e:
            return f"Error executing edit_file: {e}"


tools = [
    ReadFile(),
    WriteFile(),
    SaveMemory(),
    WritePlan(),
    ListFiles(),
    SearchCodebase(),
    RunCommand(),
    EditFile(),
]


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
