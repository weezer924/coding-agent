"""Manual probe of Sarashina tool calling inside the agent loop.

Three questions (2026-10-21 note):
  1. ja_chain      Japanese instruction -> read_file -> write_file chain
  2. ambiguous_*   deliberately vague/escaping-heavy prompts -> do the args break?
  3. stability_*   same prompt N times from a fresh conversation -> same tool_calls?

Each run gets a fresh Agent and a fresh temp working dir seeded with a copy of
tools.py, so relative paths the model writes land there, not in the repo.

Usage (from mine/):
  .venv/bin/python scripts/experiment_sarashina.py [--brain sarashina|claude]
      [--cases ja_chain,stability_en] [--repeat N] [--out DIR]

Prints one summary line per run and appends a JSON record per run to
<out>/runs.jsonl.
"""

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

MINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MINE))

from agent import Agent  # noqa: E402
from brain import ClaudeBrain, RateLimited, SarashinaBrain  # noqa: E402
from tools import ReadFile, SaveMemory, WriteFile  # noqa: E402

RW = lambda: [ReadFile(), WriteFile()]  # noqa: E731
RWM = lambda: [ReadFile(), WriteFile(), SaveMemory()]  # noqa: E731

EN_PROMPT = 'read tools.py and write a new file hello.text with "hello from sarashina"'
JA_PROMPT = (
    "tools.py を読んで、定義されているツール名と説明を一覧にした "
    "tools_list.md を書いてください"
)

CASES = {
    # ① Japanese read -> write chain
    "ja_chain": dict(prompt=JA_PROMPT, tools=RW, repeat=3),
    # ② ambiguous: no path, no such file
    "ambiguous_missing": dict(prompt="設定ファイルを読んで", tools=RW, repeat=2),
    # ② ambiguous: quotes, full-width quotes, newline inside the content arg
    "ambiguous_escape": dict(
        prompt='hello.txt に "こんにちは" と書いて、次の行に「世界」も',
        tools=RW,
        repeat=2,
    ),
    # ② near-duplicate tool definitions: which one does it pick?
    "ambiguous_tool_confusion": dict(
        prompt="この内容を覚えておいて：面接は 10/27 11:00 Google Meet",
        tools=RWM,
        repeat=2,
    ),
    # ③ stability, default temperature
    "stability_en": dict(prompt=EN_PROMPT, tools=RW, repeat=3),
    # ③ stability, temperature 0
    "stability_en_t0": dict(
        prompt=EN_PROMPT, tools=RW, repeat=3, brain_kwargs={"temperature": 0}
    ),
}

JA_RE = re.compile(r"[぀-ヿ一-鿿]")


class RecordingBrain:
    """Wraps a Brain; records tool_calls, timing and usage per think()."""

    def __init__(self, inner, max_retries=6):
        self.inner = inner
        self.rounds = []
        self.rate_limited = 0
        self.max_retries = max_retries

    def _think_with_retry(self, conversation):
        for attempt in range(self.max_retries):
            try:
                return self.inner.think(conversation)
            except RateLimited as e:
                self.rate_limited += 1
                wait = (e.retry_after or 10) + 1
                print(f"    (429, waiting {wait:.0f}s, attempt {attempt + 1})")
                time.sleep(wait)
        return self.inner.think(conversation)

    def think(self, conversation):
        t0 = time.perf_counter()
        try:
            thought = self._think_with_retry(conversation)
        except Exception as e:
            self.rounds.append(
                {"elapsed": time.perf_counter() - t0, "error": repr(e)}
            )
            raise
        self.rounds.append(
            {
                "elapsed": time.perf_counter() - t0,
                "text": thought.text,
                "tool_calls": [
                    {"name": c.name, "args": c.args, "raw_args": c.raw_args}
                    for c in thought.tool_calls
                ],
                "usage": getattr(self.inner, "last_usage", None),
            }
        )
        return thought


def make_brain(name, tools, **kwargs):
    if name == "sarashina":
        return SarashinaBrain(tools=tools, **kwargs)
    if name == "claude":
        return ClaudeBrain(tools=tools)  # kwargs ignored: baseline on defaults
    raise ValueError(name)


def run_once(case_id, case, brain_name, run_idx, out_dir):
    workdir = Path(tempfile.mkdtemp(prefix=f"{case_id}_{run_idx}_", dir=out_dir))
    shutil.copy(MINE / "tools.py", workdir / "tools.py")
    before = {p.name for p in workdir.iterdir()}

    tools = case["tools"]()
    brain = RecordingBrain(make_brain(brain_name, tools, **case.get("brain_kwargs", {})))
    agent = Agent(brain, brain_name=brain_name, tools=tools)

    cwd = os.getcwd()
    os.chdir(workdir)
    t0 = time.perf_counter()
    try:
        output = agent.handle_input(case["prompt"])
    finally:
        os.chdir(cwd)
    total = time.perf_counter() - t0

    new_files = {}
    for p in workdir.iterdir():
        if p.name not in before and p.is_file():
            new_files[p.name] = p.read_text(encoding="utf-8", errors="replace")

    tool_seq = [c["name"] for r in brain.rounds for c in r.get("tool_calls", [])]
    paths = [
        c["args"].get("path")
        for r in brain.rounds
        for c in r.get("tool_calls", [])
        if isinstance(c["args"], dict)
    ]
    parse_errors = [
        c["raw_args"]
        for r in brain.rounds
        for c in r.get("tool_calls", [])
        if c["raw_args"] is not None
    ]
    api_errors = [r["error"] for r in brain.rounds if "error" in r]

    record = {
        "case": case_id,
        "run": run_idx,
        "brain": brain_name,
        "model": getattr(brain.inner, "model", None),
        "brain_kwargs": case.get("brain_kwargs", {}),
        "prompt": case["prompt"],
        "rounds": brain.rounds,
        "n_rounds": len(brain.rounds),
        "tool_seq": tool_seq,
        "paths": paths,
        "parse_errors": parse_errors,
        "api_errors": api_errors,
        "rate_limited": brain.rate_limited,
        "total_s": round(total, 2),
        "output": output,
        "output_is_ja": bool(JA_RE.search(output or "")),
        "new_files": new_files,
        "workdir": str(workdir),
    }
    with open(out_dir / "runs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    per_round = "/".join(f"{r['elapsed']:.1f}" for r in brain.rounds)
    files = ", ".join(f"{k}:{len(v)}ch" for k, v in new_files.items()) or "-"
    print(
        f"[{brain_name}] {case_id} run{run_idx}: "
        f"tools={'→'.join(tool_seq) or '-'} paths={paths} "
        f"rounds={len(brain.rounds)} ({per_round}s, total {total:.1f}s) "
        f"parse_err={len(parse_errors)} api_err={len(api_errors)} 429s={brain.rate_limited} "
        f"files={files} ja={record['output_is_ja']}"
    )
    if output:
        print("    ↳ " + output.replace("\n", " ⏎ ")[:200])
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brain", default="sarashina", choices=["sarashina", "claude"])
    ap.add_argument("--cases", default=",".join(CASES))
    ap.add_argument("--repeat", type=int, default=None, help="override per-case repeat")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out_dir = Path(args.out or tempfile.mkdtemp(prefix="sarashina_exp_"))
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"out: {out_dir}")

    for case_id in args.cases.split(","):
        case = CASES[case_id]
        for i in range(1, (args.repeat or case["repeat"]) + 1):
            run_once(case_id, case, args.brain, i, out_dir)


if __name__ == "__main__":
    main()
