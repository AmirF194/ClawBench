#!/usr/bin/env python3
"""Fail if any Markdown file links to a repo path that does not exist.

Checks relative links and image sources in every tracked ``*.md`` file:
``[text](path)``, ``![alt](path)``, and bare ``<img src="path">``. External
URLs (http, https, mailto, data, tel) and in-page anchors are skipped — this
guards against renamed or deleted files, not against the network.

Usage: ``python scripts/check_markdown_links.py [root]`` (default: repo root).
Exit code 1 lists every broken link with its source file and line number.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "test-output"}
EXTERNAL = ("http://", "https://", "mailto:", "data:", "tel:", "//")

MD_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HTML_SRC = re.compile(r"<img[^>]*\ssrc=[\"']([^\"']+)[\"']", re.I)


def iter_markdown(root: Path):
    for path in sorted(root.rglob("*.md")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def targets(line: str):
    for match in MD_LINK.finditer(line):
        yield match.group(1).split()[0]  # drop optional "title"
    for match in HTML_SRC.finditer(line):
        yield match.group(1)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    broken: list[str] = []
    checked = 0

    for md in iter_markdown(root):
        for lineno, line in enumerate(
            md.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
        ):
            for raw in targets(line):
                target = raw.split("#")[0].strip()
                if not target or target.startswith(EXTERNAL):
                    continue
                checked += 1
                resolved = (md.parent / target).resolve()
                if not resolved.exists():
                    broken.append(f"{md.relative_to(root)}:{lineno}: {raw}")

    if broken:
        print(f"{len(broken)} broken repo-relative link(s):", file=sys.stderr)
        for item in broken:
            print(f"  {item}", file=sys.stderr)
        return 1

    print(f"all {checked} repo-relative markdown links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
