# Nanocode Coding Agent with Different Models

My own build of a minimal coding agent, Here is the introduce for each files:

| File | Owns | Knows nothing about |
|---|---|---|
| `agent.py` | the conversation list and the loop; plan/act mode (filters the tool menu by `plan_safe`); compaction when `last_input_tokens` nears `context_limit` | HTTP, file I/O |
| `brain.py` | one class per LLM provider, normalised to a `Thought`; reports `last_input_tokens` and its `context_limit` | history, tools' internals, mode |
| `tools.py` | read/write/edit/list/search/run_command/save_memory/write_plan, the JSON Schema the model sees, and each tool's `plan_safe` flag | the model, the loop |
| `memory.py` | `Memory`: one markdown file read at startup, injected as system prompt, overwritten by `save_memory`; `ToolContext`: the bag handed to every tool | the model, the loop, HTTP |
| `main.py` | the Read-Eval-Print Loop(REPL) and wiring | everything else |

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then put ANTHROPIC_API_KEY (and SARASHINA_API_KEY) in .env
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

### ch05: read + write (Sarashina)

Prompt: `read tools.py and write a new file hello.text with "hello from sarashina"`

```sh
> read tools.py and write a new file hello.text with "hello from sarashina"
8 ['read_file']
  → Writing hello.text
10 ['write_file']

The file **`hello.text`** has been created with the content:

"hello from sarashina"
```

### ch07 + ch09: plan mode, then act mode with run_command (Claude)

Setup: a scratch folder with a broken `calc.py` (`add` subtracts, `average([])` divides by zero) and a `test_calc.py` that expects the right behaviour. Run from inside that folder so `run_command` and the file tools see it:

```sh
cd /path/to/scratch-task
source /path/to/mine/.venv/bin/activate
PYTHONPATH=/path/to/mine python /path/to/mine/main.py
```

Plan mode (default). The model has no `write_file`, `edit_file` or `run_command` on its menu, so it reads, writes `PLAN.md`, and stops:

```sh
[claude:plan] > The tests in test_calc.py fail. Fix calc.py so that pytest -q passes.
  → Writing PLAN

I found two bugs in `calc.py` and saved a plan to fix them. I haven't changed any files yet, because I'm in read-only plan mode.

- **`add`:** it returns `a - b`, so `test_add` fails. The fix is to return `a + b`.
- **`average`:** an empty list raises `ZeroDivisionError`, but `test_average_empty` expects `0`.

Switch to ACT mode (`/mode act`) and I'll make both edits and run `pytest -q` to confirm.
```

Act mode. Same prompt. The model runs the tests, reads the failure, edits, re-runs, and only then reports. One turn, three tool calls, no human in the middle:

```sh
[claude:plan] > /mode act
Switched to ACT MODE

[claude:act] > The tests in test_calc.py fail. Fix calc.py so that pytest -q passes. Run the tests to confirm.
  → Running: pytest -q 2>&1 | head -50
  → Writing calc.py
  → Running: pytest -q

I fixed two bugs in `calc.py`, and `pytest -q` now passes (2 passed).

- **`add`:** it returned `a - b`, so I changed it to `a + b`.
- **`average`:** it raised `ZeroDivisionError` on an empty list. It now returns `0` for an empty list.
```

Note the first command: the model added `| head -50` on its own, because the `run_command` description says output is truncated at 5000 characters.

## Develop log

| Develop Step | State | What it added | What I Did |
|---|---|---|---|
| 01 | done | REPL: read, eval, print, loop | The outer loop never changes; every later chapter only changes `handle_input`. |
| 02 | done | One raw `requests.post` to Claude, one to Sarashina | `content` is a list of typed blocks. `stop_reason` drives the loop later. Two providers, two JSON shapes. |
| 03 | done | `Brain.think(conversation) -> Thought`, `Agent.conversation` | The API is stateless; the list in `Agent` is the only memory. A failed call must pop the user turn or the next call breaks. The model can return a `thinking` block first, so never index `content[0]`. |
| 04 | done | `Brain` base class, `BRAINS` registry, `/switch` | History is provider-neutral; only the brain converts. Roles are `user` / `assistant`, nothing else. |
| 05 | done | `ReadFile`, `WriteFile`, tool schemas, the agentic loop | Tool use is a protocol: send schemas, get back a structured call, run it, return a `tool_result` block. Assistant turns must be stored as raw blocks so ids line up. Tools return strings, never raise. Cap the loop. |
| 06 | done | `Memory` file, `ToolContext`, `SaveMemory` tool; memory goes into the system prompt | Memory is not inside the model: a file is read at startup and injected as the system prompt every call, and the model gets one tool to overwrite that file. Cross-session recall works only because the text is re-fed each time. `ToolContext` is a bag passed as the first argument to every tool so internal objects (memory) travel separately from the model's args |
| 07 | done | Plan mode: a read-only mode that blocks `write_file` until the user approves | Safety by menu, not by prompt: in plan mode the agent removes `write_file` from the tool list sent to the model and adds a `write_plan` tool, so the model physically cannot write code; `/mode act` restores the full menu. |
| 08 | done | Codebase context: `ListFiles`, `SearchCodebase`; context-window tracking via `usage.input_tokens` against a per-model limit, compaction when near the limit | `list_files` and `search_codebase` let the model find files itself; `last_input_tokens` from the API usage block is checked against `context_limit` and at 75% the history is summarized into one user message |
| 09 | done | `RunCommand` tool: run tests, feed stdout/stderr back into the loop | `run_command` returns STDOUT, STDERR and exit code (30s timeout, 5000-char truncation) so the model can run `pytest`, read the failure and fix it in one turn; `edit_file` replaces one exact match instead of rewriting the whole file; plan mode hides tools by a `plan_safe` flag; a failed compaction is caught and the turn continues. Live check: broken `calc.py` fixed and verified in 3 tool calls. |
| 10 | next | Eval: task set from a scratch repo with hidden tests, run the agent per task, record pass/fail, iterations, tokens | |

## License

MIT. The test files reference under
[optimalone/build-your-own-coding-agent](https://github.com/optimalone/build-your-own-coding-agent),
Copyright (c) 2025 Owen Ou, MIT License. The full text is in [LICENSE](LICENSE)
and applies to this repository as well.
