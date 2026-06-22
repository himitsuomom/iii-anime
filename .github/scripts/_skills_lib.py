#!/usr/bin/env python3
"""Shared helpers for the skills catalog + audit tooling.

These tools treat ``skills/iii-*/SKILL.md`` as filesystem-truth in the same way
``build_catalog.py`` did for the curriculum it was ported from: discover the
skill directories on disk, parse their frontmatter, and expose the result to the
audit, catalog-build, and docs-sync checks.

Stdlib only. Python 3.10+ (PEP 604 unions in type hints).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Iterator

# Repo root is two levels up from .github/scripts/.
ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = ROOT / "skills"
CATALOG_PATH = SKILLS_DIR / "catalog.json"

# A top-level skill folder: lowercase, hyphen-separated, prefixed with iii-.
SKILL_DIR_RE = re.compile(r"^iii-[a-z0-9]+(?:-[a-z0-9]+)*$")
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def parse_frontmatter(text: str) -> dict[str, object] | None:
    """Parse a YAML-subset frontmatter block at the top of a markdown string.

    Returns the parsed key/value mapping, or ``None`` when no frontmatter is
    present or the closing ``---`` is missing.

    Supports the subset actually used by ``SKILL.md`` files:

    - bare strings: ``key: value``
    - single/double quoted: ``key: 'value'`` / ``key: "value"``
    - inline lists: ``key: [a, b, "c"]``
    - block scalars: ``key: >-`` / ``>`` / ``|`` / ``|-`` with indented
      continuation lines (folded scalars join with spaces; literal scalars keep
      newlines).
    - comment lines beginning with ``#``
    """
    if not text.startswith("---\n"):
        return None
    # Closing delimiter: "\n---\n" inside the file, or "\n---" at EOF.
    end = text.find("\n---\n", 4)
    if end == -1 and text.endswith("\n---"):
        end = len(text) - 4
    if end == -1:
        return None

    lines = text[4:end].splitlines()
    result: dict[str, object] = {}
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        # Anchor keys at column 0: skip comments + indented (continuation) lines.
        if not raw or raw.startswith("#") or raw[0] in (" ", "\t"):
            continue
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        key = key.strip()
        if not key:
            continue
        value = value.strip()

        if value in (">", ">-", ">+", "|", "|-", "|+"):
            block: list[str] = []
            while i < len(lines) and (not lines[i] or lines[i][0] in (" ", "\t")):
                block.append(lines[i])
                i += 1
            # Trim common leading indentation, then fold or keep newlines.
            dedented = [ln.strip() for ln in block]
            # Drop trailing blank lines introduced by the block.
            while dedented and not dedented[-1]:
                dedented.pop()
            if value.startswith(">"):
                result[key] = " ".join(ln for ln in dedented if ln)
            else:
                result[key] = "\n".join(dedented)
            continue

        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            result[key] = (
                [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]
                if inner
                else []
            )
        elif (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            result[key] = value[1:-1]
        else:
            result[key] = value
    return result


def read_h1(text: str) -> str | None:
    """Return the first top-level ``# H1`` heading in a markdown string."""
    match = H1_RE.search(text)
    return match.group(1).strip() if match else None


def iter_skill_dirs(skills_dir: Path = SKILLS_DIR) -> Iterator[Path]:
    """Yield every ``skills/iii-*`` directory in sorted order."""
    if not skills_dir.is_dir():
        return
    for path in sorted(skills_dir.iterdir()):
        if path.is_dir() and path.name.startswith("iii-"):
            yield path


def relpath(path: Path, root: Path = ROOT) -> str:
    """POSIX-style path relative to the repo root (best effort)."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def md_links(text: str) -> Iterable[str]:
    """Yield the href target of every inline markdown link in ``text``."""
    for match in re.finditer(r"\[[^\]]*\]\(([^)\s#]+)(?:#[^)]*)?\)", text):
        yield match.group(1).strip()
