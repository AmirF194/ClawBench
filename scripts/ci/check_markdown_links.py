#!/usr/bin/env python3
"""Validate repository-relative links in Markdown documentation."""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "test-output",
}
FENCE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})(.*)$")
HTML_TARGET = re.compile(
    r"<(?:a|img|source|video|audio)\b[^>]*?"
    r"\s(?:href|src|poster)\s*=\s*(?:\"([^\"]+)\"|'([^']+)')",
    re.I,
)
REFERENCE_TARGET = re.compile(
    r"^[ \t]{0,3}\[(?!\^)[^\]]+\]:[ \t]*(?:<([^>]+)>|((?:\\.|\S)+))",
    re.M,
)


def markdown_files(root: Path):
    paths = set(root.rglob("*.md")) | set(root.rglob("*.markdown"))
    for path in sorted(paths):
        if not any(part in SKIP_DIRS for part in path.parts):
            yield path


def blank(text: str) -> str:
    return "".join("\n" if char == "\n" else " " for char in text)


def closing_backticks(line: str, start: int, width: int) -> int:
    marker = "`" * width
    cursor = start
    while True:
        closing = line.find(marker, cursor)
        if closing < 0:
            return -1
        before = closing > 0 and line[closing - 1] == "`"
        after_index = closing + width
        after = after_index < len(line) and line[after_index] == "`"
        if not before and not after:
            return closing
        cursor = closing + width


def mask_code(markdown: str) -> str:
    """Mask code and comments while preserving offsets and newlines."""
    masked_lines = []
    fence_char = None
    fence_length = 0

    for line in markdown.splitlines(keepends=True):
        fence = FENCE.match(line)
        if fence_char is not None:
            if fence:
                marker, remainder = fence.groups()
                if (
                    marker[0] == fence_char
                    and len(marker) >= fence_length
                    and not remainder.strip()
                ):
                    fence_char = None
                    fence_length = 0
            masked_lines.append(blank(line))
            continue

        if fence:
            marker = fence.group(1)
            fence_char = marker[0]
            fence_length = len(marker)
            masked_lines.append(blank(line))
            continue

        chars = list(line)
        cursor = 0
        while cursor < len(chars):
            if chars[cursor] != "`":
                cursor += 1
                continue
            end_of_run = cursor
            while end_of_run < len(chars) and chars[end_of_run] == "`":
                end_of_run += 1
            width = end_of_run - cursor
            closing = closing_backticks(line, end_of_run, width)
            if closing < 0:
                cursor = end_of_run
                continue
            for index in range(cursor, closing + width):
                if chars[index] != "\n":
                    chars[index] = " "
            cursor = closing + width
        masked_lines.append("".join(chars))

    masked = "".join(masked_lines)
    return re.sub(
        r"<!--.*?-->",
        lambda match: blank(match.group()),
        masked,
        flags=re.S,
    )


def markdown_inline_targets(markdown: str):
    """Parse Markdown destinations, including spaces and balanced parentheses."""
    cursor = 0
    while True:
        opening = markdown.find("](", cursor)
        if opening < 0:
            return

        index = opening + 2
        while index < len(markdown) and markdown[index].isspace():
            index += 1
        target_line = markdown.count("\n", 0, opening) + 1

        if index < len(markdown) and markdown[index] == "<":
            closing = markdown.find(">", index + 1)
            if closing >= 0:
                yield markdown[index + 1 : closing], target_line
                cursor = closing + 1
                continue

        start = index
        depth = 0
        while index < len(markdown):
            char = markdown[index]
            if char == "\\" and index + 1 < len(markdown):
                index += 2
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                if depth == 0:
                    break
                depth -= 1
            elif char.isspace() and depth == 0:
                break
            index += 1

        if index > start:
            yield markdown[start:index], target_line
        cursor = max(index + 1, opening + 2)


def line_number(markdown: str, offset: int) -> int:
    return markdown.count("\n", 0, offset) + 1


def link_targets(markdown: str):
    yield from markdown_inline_targets(markdown)
    for match in REFERENCE_TARGET.finditer(markdown):
        yield match.group(1) or match.group(2), line_number(markdown, match.start())
    for match in HTML_TARGET.finditer(markdown):
        yield match.group(1) or match.group(2), line_number(markdown, match.start())


def local_path(raw_target: str):
    target = html.unescape(raw_target.strip())
    try:
        parsed = urlsplit(target)
    except ValueError:
        return None
    if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith("/"):
        return None
    path = unquote(parsed.path)
    return re.sub(r"\\([\\`*_{}\[\]()#+\-.! ])", r"\1", path)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    broken = []
    checked = 0

    for markdown in markdown_files(root):
        text = markdown.read_text(encoding="utf-8", errors="ignore")
        for raw_target, target_line in link_targets(mask_code(text)):
            target = local_path(raw_target)
            if target is None:
                continue

            checked += 1
            resolved = (markdown.parent / target).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                broken.append(
                    f"{markdown.relative_to(root)}:{target_line}: "
                    f"{raw_target} (escapes repository)"
                )
            else:
                if not resolved.exists():
                    broken.append(
                        f"{markdown.relative_to(root)}:{target_line}: {raw_target}"
                    )

    if broken:
        print(f"{len(broken)} broken repo-relative link(s):", file=sys.stderr)
        for item in broken:
            print(f"  {item}", file=sys.stderr)
        return 1

    print(f"All {checked} repo-relative Markdown links resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
