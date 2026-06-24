#!/usr/bin/env python3
"""Verify the skills catalog docs match catalog.json (filesystem-truth).

Ported from the curriculum's ``check_readme_counts.py``. There it pinned
hardcoded README counts to ``catalog.json`` totals; here it pins the skill
*set* listed in ``skills/README.md`` and ``skills/SKILLS.md`` to the skills that
actually exist on disk (as captured in ``skills/catalog.json``). Both docs hand-
maintain a catalog table/list that silently drifts whenever a skill is added or
removed; this check fails the build when they disagree.

A skill is considered "listed" in a doc when its folder name (e.g.
``iii-core-primitives``) appears anywhere in that doc's text — every existing
listing links to ``iii-<slug>/SKILL.md`` or ``./iii-<slug>``, so the folder name
is always present in a correct listing.

Usage:
    python3 .github/scripts/check_skills_docs.py           # exit 1 on any drift
    python3 .github/scripts/check_skills_docs.py --json     # machine-readable report
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _skills_lib import CATALOG_PATH, SKILLS_DIR, relpath  # noqa: E402

DOCS = ("README.md", "SKILLS.md")


@dataclass
class Drift:
    doc: str
    kind: str  # "missing" | "stale"
    skill: str

    def to_dict(self) -> dict[str, str]:
        return {"doc": self.doc, "kind": self.kind, "skill": self.skill}


def load_catalog_names(catalog_path: Path) -> list[str]:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    skills = catalog.get("skills")
    if not isinstance(skills, list):
        raise SystemExit(f"{relpath(catalog_path)} is missing a skills[] array")
    return [str(s["name"]) for s in skills if isinstance(s, dict) and s.get("name")]


def find_drift(skills_dir: Path, catalog_names: list[str]) -> list[Drift]:
    catalog_set = set(catalog_names)
    drift: list[Drift] = []
    for name in DOCS:
        doc = skills_dir / name
        if not doc.is_file():
            continue
        text = doc.read_text(encoding="utf-8")
        # Missing: a real skill the doc never mentions.
        for skill in catalog_names:
            if skill not in text:
                drift.append(Drift(name, "missing", skill))
        # Stale: a markdown link to an iii-* skill folder that no longer exists.
        import re

        for match in re.finditer(r"iii-[a-z0-9]+(?:-[a-z0-9]+)*", text):
            referenced = match.group(0)
            if referenced not in catalog_set and referenced != "iii-hq":
                drift.append(Drift(name, "stale", referenced))
    # De-dupe stale entries (a folder name may appear many times in one doc).
    seen: set[tuple[str, str, str]] = set()
    unique: list[Drift] = []
    for d in drift:
        key = (d.doc, d.kind, d.skill)
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return unique


def render_report(drift: list[Drift]) -> str:
    if not drift:
        return "skills docs are in sync with catalog.json.\n"
    out = [f"skills docs drift detected: {len(drift)} issue(s).\n"]
    for d in drift:
        if d.kind == "missing":
            out.append(f"  skills/{d.doc}: missing skill {d.skill!r} (exists on disk, not listed)\n")
        else:
            out.append(f"  skills/{d.doc}: stale reference {d.skill!r} (listed, not on disk)\n")
    out.append("\nUpdate skills/README.md and skills/SKILLS.md to match the skill set.\n")
    return "".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--json", action="store_true", help="emit JSON report on stdout")
    parser.add_argument("--skills-dir", type=Path, default=SKILLS_DIR)
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    args = parser.parse_args(argv)

    catalog_names = load_catalog_names(args.catalog)
    drift = find_drift(args.skills_dir, catalog_names)

    if args.json:
        json.dump(
            {"ok": not drift, "skills": catalog_names, "drift": [d.to_dict() for d in drift]},
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_report(drift))
        for d in drift:
            print(f"::error file=skills/{d.doc}::{d.kind} skill {d.skill}")

    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
