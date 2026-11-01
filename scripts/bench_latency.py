"""Manual latency bench: same prompt N times per model, streamed.

Measures per run, from just before the POST:
  ttft_s    first non-empty text delta
  total_s   stream fully drained
  out_tok   completion tokens reported by the API
  decode_tps  out_tok / (total_s - ttft_s)

Hits the HTTP APIs directly with stream=true; Brain.think() is non-streaming,
so it cannot see the first token.

Usage (from mine/):
  .venv/bin/python scripts/bench_latency.py [--models sarashina3-mini,sarashina3-nano,claude-sonnet-5-5]
      [--n 20] [--max-tokens 256] [--prompt "..."] [--out runs.jsonl]
"""

import argparse
import json
import os
import statistics
import time

import requests
from dotenv import load_dotenv

load_dotenv()

SARASHINA_URL = "https://api.sarashina.ai/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

DEFAULT_PROMPT = "Pythonでリストを逆順にする方法を3つ、それぞれ1行のコード例付きで説明してください。"


class RateLimited(Exception):
    def __init__(self, retry_after):
        self.retry_after = retry_after


def _sse_data(resp):
    for line in resp.iter_lines(decode_unicode=True):
        if line and line.startswith("data:"):
            data = line[5:].strip()
            if data == "[DONE]":
                return
            yield json.loads(data)


def stream_sarashina(model, prompt, max_tokens):
    payload = {
        "model": model,
        "stream": True,  # stream_options is rejected: "disallowed fields"
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {os.getenv('SARASHINA_API_KEY')}"}
    t0 = time.perf_counter()
    ttft, out_tok, text = None, None, []
    with requests.post(SARASHINA_URL, headers=headers, json=payload, stream=True, timeout=120) as r:
        if r.status_code == 429:
            raise RateLimited(r.headers.get("Retry-After"))
        r.raise_for_status()
        for ev in _sse_data(r):
            for ch in ev.get("choices") or []:
                piece = (ch.get("delta") or {}).get("content")
                if piece:
                    ttft = ttft or time.perf_counter() - t0
                    text.append(piece)
            if ev.get("usage"):
                out_tok = ev["usage"].get("completion_tokens")
    return t0, ttft, out_tok, "".join(text)


def stream_claude(model, prompt, max_tokens):
    payload = {
        "model": model,
        "stream": True,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": os.getenv("ANTHROPIC_API_KEY"),
        "anthropic-version": "2023-06-01",
    }
    t0 = time.perf_counter()
    ttft, out_tok, text = None, None, []
    with requests.post(ANTHROPIC_URL, headers=headers, json=payload, stream=True, timeout=120) as r:
        if r.status_code == 429:
            raise RateLimited(r.headers.get("retry-after"))
        r.raise_for_status()
        for ev in _sse_data(r):
            if ev["type"] == "content_block_delta" and ev["delta"].get("type") == "text_delta":
                ttft = ttft or time.perf_counter() - t0
                text.append(ev["delta"]["text"])
            elif ev["type"] == "message_delta":
                out_tok = ev["usage"]["output_tokens"]
    return t0, ttft, out_tok, "".join(text)


def run_once(model, prompt, max_tokens):
    fn = stream_claude if model.startswith("claude") else stream_sarashina
    t0, ttft, out_tok, text = fn(model, prompt, max_tokens)
    total = time.perf_counter() - t0
    decode = out_tok / (total - ttft) if out_tok and ttft and total > ttft else None
    return {"ttft_s": ttft, "total_s": total, "out_tok": out_tok, "decode_tps": decode, "chars": len(text)}


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, round(p / 100 * (len(xs) - 1)))]


def summarize(model, recs):
    ok = [r for r in recs if "error" not in r]
    line = f"{model:<20} ok={len(ok)}/{len(recs)} 429={sum(r.get('rate_limited', 0) for r in recs)}"
    for key in ("ttft_s", "total_s", "out_tok", "decode_tps"):
        xs = [r[key] for r in ok if r[key] is not None]
        if xs:
            line += f"  {key} p50={statistics.median(xs):.2f} p90={pct(xs, 90):.2f}"
    print(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="sarashina3-mini,sarashina3-nano,claude-sonnet-5-5")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--out", default="bench_runs.jsonl")
    args = ap.parse_args()
    models = args.models.split(",")

    results = {m: [] for m in models}
    # Interleave models so a slow minute on the network hits all of them alike.
    for i in range(1, args.n + 1):
        for m in models:
            rec = {"model": m, "run": i, "rate_limited": 0}
            for _ in range(6):
                try:
                    rec.update(run_once(m, args.prompt, args.max_tokens))
                    break
                except RateLimited as e:
                    rec["rate_limited"] += 1
                    time.sleep(float(e.retry_after or 10) + 1)
                except Exception as e:
                    rec["error"] = repr(e)[:300]
                    break
            results[m].append(rec)
            with open(args.out, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if "error" in rec:
                print(f"  {m} run{i}: ERROR {rec['error']}")
            elif "ttft_s" in rec:
                print(f"  {m} run{i}: ttft={rec['ttft_s']:.2f}s total={rec['total_s']:.2f}s out={rec['out_tok']}tok")
            time.sleep(args.sleep)

    print()
    for m in models:
        summarize(m, results[m])


if __name__ == "__main__":
    main()
