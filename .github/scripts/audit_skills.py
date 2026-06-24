#!/usr/bin/env python3
"""Invariant checks across every top-level skill in ``skills/iii-*``.

Ported from the curriculum's ``audit_lessons.py``: instead of validating
``phases/NN/MM`` lesson folders it validates iii's ``skills/iii-<slug>`` skill
folders, which each ship a single ``SKILL.md`` with frontmatter.

Usage:
    python3 .github/scripts/audit_skills.py [--json] [--skills-dir DIR]

Exit codes:
    0 — clean
    1 — issues found

Rules:
    S001  folder name does not match ^iii-<slug>$
    S002  SKILL.md missing or not valid UTF-8
    S003  SKILL.md frontmatter missing, or missing name/description
    S004  frontmatter name does not equal the folder name
    S005  SKILL.md has no top-level H1 in its body
    S006  SKILL.md body shorter than the minimum byte budget
    S007  internal markdown link does not resolve on disk
    S008  skill is not listed in skills/README.md or skills/SKILLS.md
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _skills_lib import (  # noqa: E402
    ROOT,
    SKILLS_DIR,
    SKILL_DIR_RE,
    iter_skill_dirs,
    md_links,
    parse_frontmatter,
    read_h1,
    relpath,
)

MIN_BODY_BYTES = 400
CATALOG_DOCS = ("README.md", "SKILLS.md")


@dataclass
class Issue:
    rule: str
    skill: str
    file: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"rule": self.rule, "skill": self.skill, "file": self.file, "message": self.message}


@dataclass
class Audit:
    skills_dir: Path = SKILLS_DIR
    skills_checked: int = 0
    issues: list[Issue] = field(default_factory=list)

    def add(self, rule: str, skill: Path, file: Path | None, message: str) -> None:
        self.issues.append(
            Issue(rule, relpath(skill), relpath(file) if file else relpath(skill), message)
        )


def _catalog_doc_text(skills_dir: Path) -> str:
    blobs = []
    for name in CATALOG_DOCS:
        doc = skills_dir / name
        if doc.is_file():
            try:
                blobs.append(doc.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                continue
    return "\n".join(blobs)


def audit_skill(audit: Audit, skill: Path, catalog_text: str) -> None:
    audit.skills_checked += 1

    if not SKILL_DIR_RE.match(skill.name):
        audit.add("S001", skill, None, f"folder name does not match iii-<slug>: {skill.name!r}")
        return

    doc = skill / "SKILL.md"
    if not doc.is_file():
        audit.add("S002", skill, doc, "missing SKILL.md")
        return
    try:
        text = doc.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        audit.add("S002", skill, doc, "SKILL.md is not valid UTF-8")
        return

    meta = parse_frontmatter(text)
    if meta is None:
        audit.add("S003", skill, doc, "SKILL.md has no frontmatter block")
    else:
        name = str(meta.get("name", "")).strip()
        description = str(meta.get("description", "")).strip()
        if not name or not description:
            missing = [k for k in ("name", "description") if not str(meta.get(k, "")).strip()]
            audit.add("S003", skill, doc, f"frontmatter missing {missing}")
        if name and name != skill.name:
            audit.add(
                "S004",
                skill,
                doc,
                f"frontmatter name {name!r} does not match folder {skill.name!r}",
            )

    # Body = everything after the frontmatter block (if any).
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            body = text[end + 5 :]
    if read_h1(body) is None:
        audit.add("S005", skill, doc, "SKILL.md body has no top-level H1")
    if len(body.encode("utf-8")) < MIN_BODY_BYTES:
        audit.add(
            "S006",
            skill,
            doc,
            f"SKILL.md body shorter than {MIN_BODY_BYTES} bytes (got {len(body.encode('utf-8'))})",
        )

    seen: set[str] = set()
    for href in md_links(text):
        if href in seen:
            continue
        seen.add(href)
        if href.startswith(("http://", "https://", "mailto:", "data:", "tel:")):
            continue
        target = (ROOT / href.lstrip("/")) if href.startswith("/") else (doc.parent / href)
        if not target.exists():
            audit.add("S007", skill, doc, f"internal link does not resolve: {href!r}")

    if catalog_text and skill.name not in catalog_text:
        audit.add(
            "S008",
            skill,
            audit.skills_dir / "README.md",
            f"{skill.name!r} is not referenced in {' or '.join(CATALOG_DOCS)}",
        )


def render_report(audit: Audit) -> str:
    by_rule: dict[str, int] = {}
    for issue in audit.issues:
        by_rule[issue.rule] = by_rule.get(issue.rule, 0) + 1
    lines = [
        f"audit_skills.py — {audit.skills_checked} skill(s) checked, {len(audit.issues)} issue(s)"
    ]
    if audit.issues:
        lines.append("")
        for issue in audit.issues:
            lines.append(f"  [{issue.rule}] {issue.file}: {issue.message}")
        lines.append("")
        lines.append("Summary by rule:")
        for rule in sorted(by_rule):
            lines.append(f"  {rule}: {by_rule[rule]}")
    return "\n".join(lines)


def run_audit(skills_dir: Path = SKILLS_DIR) -> Audit:
    audit = Audit(skills_dir=skills_dir)
    catalog_text = _catalog_doc_text(skills_dir)
    for skill in iter_skill_dirs(skills_dir):
        audit_skill(audit, skill, catalog_text)
    return audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON report on stdout")
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=SKILLS_DIR,
        help="skills directory to audit (default: <repo>/skills)",
    )
    args = parser.parse_args(argv)

    audit = run_audit(args.skills_dir)

    if args.json:
        json.dump(
            {
                "skills_checked": audit.skills_checked,
                "issues": [issue.to_dict() for issue in audit.issues],
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_report(audit) + "\n")
        for issue in audit.issues:
            print(f"::error file={issue.file}::[{issue.rule}] {issue.message}")

    return 1 if audit.issues else 0


if __name__ == "__main__":
    sys.exit(main())
