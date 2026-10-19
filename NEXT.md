# 下次开工

## 现状（2026-10-19）
- ch05 完成并 commit：Claude 与 Sarashina 都能用 read_file / write_file，一次输入可连续多圈调工具。
- Sarashina 走 OpenAI 方言，桥在 `SarashinaBrain` 里：`_tool_definitions`（工具定义）、`_to_messages`（历史，发送方向）、`_to_blocks`（回复，接收方向）。历史统一存 Claude block 格式，Agent 与 tools 不感知厂商。

## 下一步：ch06 持久记忆
```bash
cp ../reference/ch06/test_nanocode.py tests/ && .venv/bin/pytest -q
```
看失败清单，照 ch05 的节奏：先读测试，写代码，再跑。

## 面试一句话
书里三家 Brain 都走 Anthropic 兼容端点，没做过格式翻译；我用 Sarashina 自己写了双向桥：历史统一按 Claude block 存，OpenAI 风格的厂商在 Brain 内进出各翻一次，Agent 和 tools 一行不改。
