#!/usr/bin/env python3
"""Build a machine-readable catalog of every top-level iii skill.

Ported from the curriculum's ``build_catalog.py``. Walks ``skills/iii-*`` on
disk and emits a single JSON document that is filesystem-truth: the skill set,
each skill's title (H1), frontmatter description, byte size, and totals. The
catalog is checked in and consumed by:

  - check_skills_docs.py  — keeps skills/README.md + SKILLS.md in sync
  - skills/site/build.js  — generates the static skills explorer data

Usage:
    python3 .github/scripts/build_skills_catalog.py            # write skills/catalog.json
    python3 .github/scripts/build_skills_catalog.py --stdout   # print, do not touch repo
    python3 .github/scripts/build_skills_catalog.py --check    # exit 1 if on-disk catalog is stale

Output shape (schema_version 1):
    {
      "schema_version": 1,
      "totals": {"skills": 6},
      "skills": [
        {"name": "iii-core-primitives", "title": "Core Primitives",
         "description": "...", "path": "skills/iii-core-primitives",
         "doc": "skills/iii-core-primitives/SKILL.md", "bytes": 12345}
      ]
    }
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _skills_lib import (  # noqa: E402
    CATALOG_PATH,
    SKILLS_DIR,
    iter_skill_dirs,
    parse_frontmatter,
    read_h1,
    relpath,
)


def slug_to_title(slug: str) -> str:
    body = slug[len("iii-") :] if slug.startswith("iii-") else slug
    return " ".join(word.capitalize() for word in body.split("-"))


def build_skill_entry(skill_dir: Path) -> dict[str, object] | None:
    doc = skill_dir / "SKILL.md"
    if not doc.is_file():
        return None
    try:
        text = doc.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    meta = parse_frontmatter(text) or {}
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            body = text[end + 5 :]
    return {
        "name": str(meta.get("name", "")).strip() or skill_dir.name,
        "title": read_h1(body) or slug_to_title(skill_dir.name),
        "description": str(meta.get("description", "")).strip(),
        "path": relpath(skill_dir),
        "doc": relpath(doc),
        "bytes": len(body.encode("utf-8")),
    }


def build_catalog(skills_dir: Path = SKILLS_DIR) -> dict[str, object]:
    skills = []
    for skill_dir in iter_skill_dirs(skills_dir):
        entry = build_skill_entry(skill_dir)
        if entry is not None:
            skills.append(entry)
    return {
        "schema_version": 1,
        "totals": {"skills": len(skills)},
        "skills": skills,
    }


def serialize(catalog: dict[str, object]) -> str:
    return json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=CATALOG_PATH, help="output path")
    parser.add_argument("--stdout", action="store_true", help="write to stdout, do not touch repo")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the on-disk catalog matches the filesystem; exit 1 if stale",
    )
    parser.add_argument("--skills-dir", type=Path, default=SKILLS_DIR)
    args = parser.parse_args(argv)

    catalog = build_catalog(args.skills_dir)
    payload = serialize(catalog)

    if args.stdout:
        sys.stdout.write(payload)
        return 0

    if args.check:
        existing = args.out.read_text(encoding="utf-8") if args.out.is_file() else ""
        if existing != payload:
            sys.stderr.write(
                f"::error::{relpath(args.out)} is out of date — "
                f"run `python3 .github/scripts/build_skills_catalog.py`\n"
            )
            return 1
        sys.stdout.write(f"{relpath(args.out)} is up to date ({catalog['totals']['skills']} skills)\n")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(payload, encoding="utf-8")
    sys.stdout.write(f"catalog: {relpath(args.out)} (skills={catalog['totals']['skills']})\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
