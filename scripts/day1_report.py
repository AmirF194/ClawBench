#!/usr/bin/env python3
"""Turn a batch-summary.json into a Day-1 results post draft.

Reads the batch summary written by `clawbench-batch` (and, optionally, a
rescore summary produced by `clawbench-rescore`) and prints a Markdown post
draft: headline numbers, per-status breakdown, an X-thread skeleton, and a
Chinese blurb. Purely local formatting — no network calls.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.1f}%" if d else "n/a"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("batch_summary", help="path to batch-summary.json")
    ap.add_argument("--model", default=None, help="model name for the headline")
    ap.add_argument(
        "--rescore-summary",
        default=None,
        help="optional eval_results summary.json from clawbench-rescore",
    )
    args = ap.parse_args()

    s = json.loads(Path(args.batch_summary).read_text(encoding="utf-8"))
    jobs = s.get("jobs", [])
    totals = s.get("totals", {})
    model = args.model or (jobs[0]["model"] if jobs else "unknown-model")
    n = len(jobs)
    passed = totals.get("passed", 0)
    errors = totals.get("error", 0)

    reward_line = ""
    if args.rescore_summary and Path(args.rescore_summary).exists():
        r = json.loads(Path(args.rescore_summary).read_text(encoding="utf-8"))
        # rescore summaries vary by rubric config; surface whatever is present
        found = {
            k: v
            for k, v in r.items()
            if isinstance(v, (int, float))
            and ("reward" in k or "pass" in k or "judge" in k)
        }
        if found:
            pretty = ", ".join(f"{k}={v}" for k, v in sorted(found.items()))
            reward_line = f"- Judge (two-stage): {pretty}\n"

    print(
        f"""# Day-1 ClawBench results — {model}

- Corpus: V2 ({n} tasks, live websites) · harness: hermes
- **Intercepted: {passed}/{n} ({pct(passed, n)})** (Stage 1, deterministic)
{reward_line}- Infra errors: {errors} (excluded runs are re-run before publishing)
- Elapsed: {s.get("elapsed_seconds", "?")}s · concurrency {s.get("max_concurrent", "?")}

Full five-layer traces will land in the public Trace dataset; leaderboard:
https://claw-bench.com/leaderboard

## X thread

1/ {model} dropped — we ran it on ClawBench (everyday tasks on live websites)
within a day. Result: {pct(passed, n)} of {n} tasks reached a valid final
request. Details + traces below 🧵
2/ What ClawBench measures: can an agent actually order food, book travel,
apply for jobs on the real web — graded by request interception + LLM judge,
not vibes.
3/ [Insert 2-3 notable failures/successes from the traces]
4/ How it compares: current top is claude-opus-4-7 at 54.6% intercepted /
44.6% reward. Leaderboard: claw-bench.com/leaderboard
5/ Everything is open: tasks, judge, and full five-layer traces of every run.
Repo: github.com/TIGER-AI-Lab/ClawBench
6/ Reproduce this row: `clawbench-reproduce --model {model}` — scores are
stable within ±2 pp.

## 中文短版(知乎/公众号)

{model} 发布后 24 小时,我们在 ClawBench(真实网站上的日常任务基准)上完成了
第三方评测:{n} 个任务中 {passed} 个到达有效最终请求({pct(passed, n)})。
全部五层轨迹(录屏/截图/HTTP/动作/agent 消息)公开可查,欢迎复现:
github.com/TIGER-AI-Lab/ClawBench
"""
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
