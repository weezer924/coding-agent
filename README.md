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
.venv/bin/python nanocode.py
```

Commands inside the Read-Eval-Print Loop: `/q` quits, `/switch` toggles between the brains in
`BRAINS` while keeping the conversation.

## Test

```bash
.venv/bin/pytest -q
```

`test_nanocode.py` use a `FakeBrain`, so no API key is needed. 
`test_anthropic_api.py` and `test_sarashina_api.py` are manual probes that hit the real APIs; 


## Develop log

| Develop Ch | State | What it added | What I Did |
|---|---|---|---|
| 01 | done | REPL: read, eval, print, loop | The outer loop never changes; every later chapter only changes `handle_input`. |
| 02 | done | One raw `requests.post` to Claude, one to Sarashina | `content` is a list of typed blocks. `stop_reason` drives the loop later. Two providers, two JSON shapes. |
| 03 | done | `Brain.think(conversation) -> Thought`, `Agent.conversation` | The API is stateless; the list in `Agent` is the only memory. A failed call must pop the user turn or the next call breaks. The model can return a `thinking` block first, so never index `content[0]`. |
| 04 | done | `Brain` base class, `BRAINS` registry, `/switch` | History is provider-neutral; only the brain converts. Roles are `user` / `assistant`, nothing else. |
| 05 | in progress | `ReadFile`, `WriteFile`, tool schemas, the agentic loop | Tool use is a protocol: send schemas, get back a structured call, run it, return a `tool_result` block. Assistant turns must be stored as raw blocks so ids line up. Tools return strings, never raise. Cap the loop. |
| 06–09 | next | memory file, plan mode, codebase search, run commands and feed errors back | |