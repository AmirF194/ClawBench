"""Main entry point for the ClawBench adapter. Do not modify the standard flags.

Constructs ClawBenchAdapter and calls run() to generate tasks in the Harbor
format at the configured output directory.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .adapter import ClawBenchAdapter

# Default output dir: <harbor repo>/datasets/clawbench
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[4] / "datasets" / "clawbench"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--task-ids", nargs="+", default=None)
    # Adapter-specific flags
    parser.add_argument(
        "--cases-dir",
        type=Path,
        default=None,
        help="ClawBench corpus (defaults to the bundled test-cases/v2)",
    )
    parser.add_argument("--org", default="clawbench", help="Task name org prefix")
    parser.add_argument(
        "--docker-image",
        default=None,
        help="Prebuilt runtime image; omit to ship environment/ per task",
    )
    args = parser.parse_args()

    adapter = ClawBenchAdapter(
        args.output_dir,
        overwrite=args.overwrite,
        limit=args.limit,
        task_ids=args.task_ids,
        cases_dir=args.cases_dir,
        org=args.org,
        docker_image=args.docker_image,
    )
    raise SystemExit(adapter.run())


if __name__ == "__main__":
    main()
