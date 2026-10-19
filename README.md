# Nanocode Coding Agent with Different Models

My own build of a minimal coding agent, 
idea from [optimalone/build-your-own-coding-agent](https://github.com/optimalone/build-your-own-coding-agent).

Here is the introduce for each files:

| File | Owns | Knows nothing about |
|---|---|---|
| `agent.py` | the conversation list and the loop | HTTP, file I/O |
| `brain.py` | one class per LLM provider, normalised to a `Thought` | history, tools' internals |
| `tools.py` | file read/write, the JSON Schema the model sees | the model, the loop |
| `main.py` | the Read-Eval-Print Loop(REPL) and wiring | everything else |

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r ../reference/requirements.txt
cp ../reference/.env.example .env   # then put ANTHROPIC_API_KEY (and SARASHINA_API_KEY) in .env
```

## Run

```bash
.venv/bin/python main.py
```

Commands inside the Read-Eval-Print Loop: `/q` quits, `/switch` toggles between the brains in
`BRAINS` while keeping the conversation.

## Test

```bash
.venv/bin/pytest -q
```

`tests/test_main.py` It uses a `FakeBrain`, so no API key is needed. 
`scripts/probe_anthropic.py` and `scripts/probe_sarashina.py` are manual probes that hit the real APIs; 

## Test result 

Prompts: "read tools.py and write a new file hello.text with "hello from sarashina"

Result:
```sh
> read tools.py and write a new file hello.text with "hello from sarashina"
8 ['read_file']
  → Writing hello.text
10 ['write_file']

The file **`hello.text`** has been created with the content:

"hello from sarashina"

Let me know if you’d like to read it back, modify it, or work with any other files!
```

## Develop log

| Develop Ch | State | What it added | What I Did |
|---|---|---|---|
| 01 | done | REPL: read, eval, print, loop | The outer loop never changes; every later chapter only changes `handle_input`. |
| 02 | done | One raw `requests.post` to Claude, one to Sarashina | `content` is a list of typed blocks. `stop_reason` drives the loop later. Two providers, two JSON shapes. |
| 03 | done | `Brain.think(conversation) -> Thought`, `Agent.conversation` | The API is stateless; the list in `Agent` is the only memory. A failed call must pop the user turn or the next call breaks. The model can return a `thinking` block first, so never index `content[0]`. |
| 04 | done | `Brain` base class, `BRAINS` registry, `/switch` | History is provider-neutral; only the brain converts. Roles are `user` / `assistant`, nothing else. |
| 05 | done | `ReadFile`, `WriteFile`, tool schemas, the agentic loop | Tool use is a protocol: send schemas, get back a structured call, run it, return a `tool_result` block. Assistant turns must be stored as raw blocks so ids line up. Tools return strings, never raise. Cap the loop. |
| 06 | next | `Memory` file, `ToolContext`, `SaveMemory` tool; memory goes into the system prompt | |
| 07 | | Plan mode: a read-only mode that blocks `write_file` until the user approves | |
| 08 | | Codebase context: `ListFiles`, `SearchCodebase`, context compaction | |
| 09 | | `RunCommand` tool: run tests, feed stdout/stderr back into the loop | |
| 10 | | Local models via Ollama, context-window detection | |
| 11 | | Web search tool (DuckDuckGo) | |
| 12 | | Capstone: build a Snake game end to end with the agent | |

## License

MIT. The test files reference under
[optimalone/build-your-own-coding-agent](https://github.com/optimalone/build-your-own-coding-agent),
Copyright (c) 2025 Owen Ou, MIT License. The full text is in [LICENSE](LICENSE)
and applies to this repository as well.
