#!/usr/bin/env python3
"""Watch for newly released frontier models and open a Day-1 eval runbook issue.

Polls the public OpenRouter model catalog (no key required) for models from
frontier vendors created within the last --days window, drops anything already
reported in a previous issue (--seen-file), and writes a ready-to-run Day-1
evaluation checklist + vendor-outreach template to --out. The GitHub Actions
workflow opens an issue from that file; the actual benchmark run happens on
maintainer infrastructure, never in CI.

Exit code is always 0; an empty/absent --out file means "nothing new".
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

CATALOG_URL = "https://openrouter.ai/api/v1/models"

# Vendors whose new releases warrant a Day-1 ClawBench run.
FRONTIER_PREFIXES = (
    "anthropic/",
    "openai/",
    "google/",
    "x-ai/",
    "deepseek/",
    "moonshotai/",
    "z-ai/",
    "minimax/",
    "qwen/",
    "meta-llama/",
    "mistralai/",
)

RUNBOOK = """\
### Runbook — {model_id}

- [ ] Add `{model_id}` to `models/models.yaml` (OpenRouter route or native API)
- [ ] Smoke: `clawbench-batch --models {model_id} --cases-suite v1-lite --all-cases --harness hermes --no-judge`
- [ ] Full V2: `clawbench-batch --models {model_id} --cases-suite v2 --all-cases --harness hermes --no-judge --max-concurrent 3`
- [ ] Score: `clawbench-rescore <output-dir> --judge-model deepseek-v4-pro --rubric both`
- [ ] Add row to the leaderboard (`leaderboard/results.csv` PR) + claw-bench.com
- [ ] Draft the results post: `python scripts/day1_report.py <output-dir>/batch-summary.json --model {model_id}`
- [ ] Publish thread (X + 知乎/公众号) linking the leaderboard

<details>
<summary>Vendor outreach template</summary>

> Subject: {model_short} on ClawBench — Day-1 third-party browser-agent results
>
> Hi — we run ClawBench (github.com/TIGER-AI-Lab/ClawBench, arXiv:2604.08523),
> an open benchmark of everyday tasks on live websites. We evaluated
> {model_short} within days of release; results and full five-layer traces are
> public. Happy to coordinate on future releases (pre-release runs under NDA
> possible) or have the row cited in your model card / technical report — Li
> Auto's Mach-Mind-4-Flash report already reports ClawBench results.

</details>
"""


def fetch_catalog() -> list[dict]:
    req = urllib.request.Request(
        CATALOG_URL, headers={"User-Agent": "clawbench-day1-watch"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp).get("data", [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2, help="release window to report")
    ap.add_argument("--out", default="day1-candidates.md")
    ap.add_argument("--seen-file", default=None, help="text dump of previous issues")
    args = ap.parse_args()

    seen = ""
    if args.seen_file and Path(args.seen_file).exists():
        seen = Path(args.seen_file).read_text(encoding="utf-8")

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    fresh = []
    for m in fetch_catalog():
        mid = m.get("id", "")
        if not mid.startswith(FRONTIER_PREFIXES) or mid.endswith(":free"):
            continue
        created = m.get("created")
        if not created or datetime.fromtimestamp(created, tz=timezone.utc) < cutoff:
            continue
        if re.search(re.escape(mid), seen):
            continue
        fresh.append(m)

    if not fresh:
        print("no new frontier models")
        return 0

    lines = [
        "New frontier model release(s) detected on OpenRouter — candidates for a",
        "**Day-1 ClawBench evaluation**. Runbook per model below; close as",
        "not-planned for minor variants not worth a full run.",
        "",
        "cc @Perry2004",
        "",
    ]
    for m in fresh:
        mid = m["id"]
        short = mid.split("/", 1)[-1]
        when = datetime.fromtimestamp(m["created"], tz=timezone.utc).strftime(
            "%Y-%m-%d"
        )
        lines.append(f"## `{mid}` (listed {when})")
        lines.append("")
        lines.append(RUNBOOK.format(model_id=mid, model_short=short))
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(fresh)} candidate model(s) written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
