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

| Develop Step | State | What it added | What I Did |
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


## About memory

# 启动
# main.py：Memory(".nanocode/memory.md")。memory.py 检查文件，不存在就写默认文字，memory.content 里有默认内容。
# main.py：建 Brain 和 Agent，把同一个 memory 对象传给两边。agent.py 里 self.context = ToolContext(memory=memory)。

# 你输入「记忆一下，我喜欢苹果」
# 3. main.py：input() 收到这句，调 agent.handle_input(...)。
# 4. agent.py：不是 /q 也不是 /switch，append 一条 role: user 进 self.conversation，进入循环。

# 第 1 圈
# 5. agent.py：调 self.brain.think(self.conversation)。
# 6. brain.py：拼 payload，messages 是历史，tools 是三个工具的定义，system 是 self.memory.content（默认文字）。发给 Claude。
# 7. Claude 看到 system 里的记忆、工具列表里有 save_memory、用户说「记忆一下」，回一个 tool_use 块：name: save_memory，input: {"content": "用户喜欢苹果"}，可能带一句文字。
# 8. brain.py：_parse_response 把块列表拆成 Thought，tool_calls 里有一个 ToolCall。
# 9. agent.py：把 raw_content 以 assistant 身份 append 进历史。有 tool_calls，不 break。
# 10. agent.py：_execute_tool("save_memory", {"content": "..."})，get_tool 找到 SaveMemory，调 tool.execute(self.context, content="...")。
# 11. tools.py：SaveMemory.execute 从 context.memory 拿到 Memory 对象，调 memory.save(content)。
# 12. memory.py：save 更新 self.content，打开 .nanocode/memory.md 写入。文件此刻已变。
# 13. tools.py：返回「Memory updated successfully!」。
# 14. agent.py：包成 tool_result 块，以 user 身份 append 进历史。回到循环顶。

# 第 2 圈
# 15. brain.py：再拼 payload。注意 system 现在是新的 memory.content，因为 Brain 和 Agent 拿的是同一个对象。
# 16. Claude 看到工具结果，回一句文字「好的，我记住了」，没有 tool_calls。
# 17. agent.py：append assistant 轮次，收集文字，没有 tool_calls，break。返回文字。
# 18. main.py：print 出来。

# 退出再启动
# 19. main.py：Memory(...) 发现文件存在，读进 content：「用户喜欢苹果」。
# 20. 你问「我喜欢什么水果」，第 1 圈 brain.py 把它放进 system，Claude 直接答「苹果」，不需要任何工具。