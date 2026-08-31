"""Build Harbor registry / manifest files from a generated ClawBench dataset.

Two outputs, both derived from the task directories on disk so they never
drift from what is committed:

* ``registry.json`` — the Harbor *git registry* consumed by
  ``harbor run --repo TIGER-AI-Lab/ClawBench -d clawbench-v2``. Each task entry
  is a repo-relative ``path``; ``git_url`` is omitted so Harbor resolves it
  against the repo the registry was fetched from.
* ``harbor/dataset.toml`` — the *Hub* manifest consumed by ``harbor publish``.
  Task digests are recomputed with Harbor's own Packager hash when the
  ``harbor`` package is importable (``uv run --with harbor==0.22.0``),
  otherwise the existing digests are kept.
"""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def task_dirs(dataset_dir: Path) -> list[Path]:
    return sorted(p.parent for p in dataset_dir.glob("*/task.toml"))


def task_name(task_dir: Path) -> str:
    config = tomllib.loads((task_dir / "task.toml").read_text())
    return config["task"]["name"]


def build_registry(
    dataset_dir: Path, name: str, version: str, description: str
) -> dict:
    tasks = [
        {
            "name": task_name(d).split("/", 1)[1],
            "path": d.relative_to(ROOT).as_posix(),
        }
        for d in task_dirs(dataset_dir)
    ]
    return [
        {
            "name": name,
            "version": version,
            "description": description,
            "tasks": tasks,
        }
    ]


def task_digest(task_dir: Path) -> str | None:
    """Same digest ``harbor add`` records (Packager.compute_content_hash)."""
    try:
        from harbor.publisher.packager import Packager  # type: ignore
    except ImportError:
        return None
    content_hash, _files = Packager.compute_content_hash(task_dir)
    return f"sha256:{content_hash}"


def update_manifest(dataset_dir: Path, manifest: Path) -> int:
    text = manifest.read_text()
    head, _, _ = text.partition("[[tasks]]")
    existing = {
        m.group(1): m.group(2)
        for m in re.finditer(
            r'\[\[tasks\]\]\s*\nname = "([^"]+)"\s*\ndigest = "([^"]+)"', text
        )
    }
    entries = []
    for d in task_dirs(dataset_dir):
        name = task_name(d)
        digest = task_digest(d) or existing.get(name, "sha256:UNSYNCED")
        entries.append(f'[[tasks]]\nname = "{name}"\ndigest = "{digest}"\n')
    manifest.write_text(head.rstrip("\n") + "\n\n" + "\n".join(entries))
    return len(entries)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--name", default="clawbench-v2")
    parser.add_argument("--version", default="1.0")
    parser.add_argument(
        "--description",
        default=(
            "ClawBench: everyday tasks on live consumer websites, scored by "
            "request interception + LLM judge. https://claw-bench.com"
        ),
    )
    parser.add_argument("--output", type=Path, help="Write registry.json here")
    parser.add_argument("--manifest", type=Path, help="Update this dataset.toml")
    args = parser.parse_args()

    dataset_dir = args.dataset_dir.resolve()
    if args.output:
        entry = build_registry(dataset_dir, args.name, args.version, args.description)[
            0
        ]
        registry = []
        if args.output.exists():
            registry = [
                e for e in json.loads(args.output.read_text()) if e["name"] != args.name
            ]
        registry.append(entry)
        registry.sort(key=lambda e: e["name"])
        args.output.write_text(json.dumps(registry, indent=2) + "\n")
        print(f"registry: {len(entry['tasks'])} tasks ({args.name}) -> {args.output}")
    if args.manifest:
        n = update_manifest(dataset_dir, args.manifest)
        print(f"manifest: {n} tasks -> {args.manifest}")
    if not (args.output or args.manifest):
        parser.error("pass --output and/or --manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
