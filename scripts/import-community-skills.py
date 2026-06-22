#!/usr/bin/env python3
"""Import awesome-claude-code resources into iii-installable community skills.

awesome-claude-code (https://github.com/anthropics/awesome-claude-code) curates
slash-commands, CLAUDE.md files, workflows, and official docs for Claude Code. It
ships the open-source-licensed copies under its ``resources/`` tree and a
``THE_RESOURCES_TABLE.csv`` catalog with display names, authors, licenses, and
descriptions.

This script converts each of those resources into the iii skill format -- one
folder per resource containing a ``SKILL.md`` with ``name``/``description``
frontmatter plus source attribution -- so the whole set is installable through
the same skills tooling as the core iii skills:

    npx skills add iii-hq/iii/community-skills
    npx skills add iii-hq/iii/community-skills --skill commit

Usage:
    python scripts/import-community-skills.py --source /path/to/awesome-claude-code

The generated ``community-skills/`` directory is committed to the repo; rerun
this script (pointed at a fresh awesome-claude-code checkout) to refresh it.
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
from pathlib import Path

# Resource categories to import, mapped to a short, stable provenance tag used in
# the generated catalog. Order controls catalog grouping.
CATEGORIES: dict[str, str] = {
    "slash-commands": "Slash Command",
    "claude.md-files": "CLAUDE.md File",
    "workflows-knowledge-guides": "Workflow / Knowledge Guide",
    "official-documentation": "Official Documentation",
}

# Catalog section headings keyed by provenance tag (avoids naive pluralization).
SECTION_HEADINGS: dict[str, str] = {
    "Slash Command": "Slash Commands",
    "CLAUDE.md File": "CLAUDE.md Files",
    "Workflow / Knowledge Guide": "Workflows & Knowledge Guides",
    "Official Documentation": "Official Documentation",
}

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "community-skills"

# Files that describe rather than constitute a resource; never treated as the
# primary content body.
_README_NAMES = {"readme.md", "readme"}


def sanitize(name: str) -> str:
    """Mirror awesome-claude-code's filename sanitization for CSV<->folder match."""
    name = re.sub(r'[<>:"/\\|?*,;]', "", name)
    name = re.sub(r"\s+", "-", name)
    return name.strip("-.")[:255]


def load_catalog(source: Path) -> dict[str, dict[str, str]]:
    """Index THE_RESOURCES_TABLE.csv by sanitized display name."""
    csv_path = source / "THE_RESOURCES_TABLE.csv"
    catalog: dict[str, dict[str, str]] = {}
    if not csv_path.exists():
        return catalog
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            catalog[sanitize(row["Display Name"])] = row
    return catalog


def first_heading(text: str) -> str | None:
    """Return the first markdown heading or non-empty line, trimmed."""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("---"):
            continue
        return line.lstrip("#").strip() or None
    return None


def fold_description(desc: str) -> str:
    """Collapse whitespace; keep frontmatter on one logical line."""
    return re.sub(r"\s+", " ", desc).strip()


def pick_primary_file(files: list[Path]) -> Path | None:
    """Choose the file whose content best represents the resource."""
    non_readme = [f for f in files if f.name.lower() not in _README_NAMES]
    pool = non_readme or files
    # Prefer a slash-command/CLAUDE.md style markdown body if present.
    md = [f for f in pool if f.suffix.lower() == ".md"]
    return (md or pool)[0] if pool else None


def make_skill(
    *,
    skill_name: str,
    category_label: str,
    resource_dir: Path,
    row: dict[str, str] | None,
) -> tuple[str, str]:
    """Build SKILL.md content. Returns (skill_name, one-line catalog description)."""
    files = sorted(p for p in resource_dir.rglob("*") if p.is_file())
    primary = pick_primary_file(files)
    primary_text = primary.read_text(encoding="utf-8", errors="replace") if primary else ""

    display = row["Display Name"] if row else resource_dir.name
    author = (row.get("Author Name") or "").strip() if row else ""
    author_link = (row.get("Author Link") or "").strip() if row else ""
    license_ = (row.get("License") or "").strip() if row else ""
    source_link = ""
    if row:
        source_link = (row.get("Primary Link") or row.get("Secondary Link") or "").strip()

    raw_desc = (row.get("Description") or "").strip() if row else ""
    if not raw_desc:
        raw_desc = first_heading(primary_text) or f"{category_label}: {display}"
    description = fold_description(f"{raw_desc} ({category_label}, via awesome-claude-code).")

    # Frontmatter
    lines = ["---", f"name: {skill_name}", "description: >-"]
    for chunk in _wrap(description, 96):
        lines.append(f"  {chunk}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {display}")
    lines.append("")

    # Attribution
    attribution: list[str] = []
    if author:
        attribution.append(f"- **Author:** [{author}]({author_link})" if author_link else f"- **Author:** {author}")
    if license_:
        attribution.append(f"- **License:** {license_}")
    if source_link:
        attribution.append(f"- **Source:** {source_link}")
    attribution.append("- **Imported from:** [awesome-claude-code](https://github.com/anthropics/awesome-claude-code)")
    attribution.append(f"- **Category:** {category_label}")
    lines.extend(attribution)
    lines.append("")

    # Body: inline the primary content; list any extra files alongside.
    if primary_text.strip():
        body = primary_text.strip()
        # Demote a leading top-level heading so it nests under our H1.
        body = re.sub(r"^#(?!#)", "##", body, count=1)
        lines.append(body)
        lines.append("")

    extras = [f for f in files if f != primary]
    if extras:
        lines.append("## Additional Files")
        lines.append("")
        for f in extras:
            rel = f.relative_to(resource_dir).as_posix()
            lines.append(f"- [`{rel}`](./{rel})")
        lines.append("")

    return "\n".join(lines), description


def _wrap(text: str, width: int) -> list[str]:
    out: list[str] = []
    line = ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return out or [text]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Path to an awesome-claude-code checkout (contains resources/ and the CSV)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for generated skills (default: community-skills/)",
    )
    args = parser.parse_args()

    source: Path = args.source
    output: Path = args.output
    if not (source / "resources").is_dir():
        parser.error(f"{source} does not look like an awesome-claude-code checkout (no resources/)")

    catalog = load_catalog(source)

    # Fresh output, but preserve a hand-written README if one exists.
    if output.exists():
        for child in output.iterdir():
            if child.name == "README.md":
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    output.mkdir(parents=True, exist_ok=True)

    used_names: set[str] = set()
    grouped: dict[str, list[tuple[str, str]]] = {label: [] for label in CATEGORIES.values()}

    for category, label in CATEGORIES.items():
        cat_dir = source / "resources" / category
        if not cat_dir.is_dir():
            continue
        for resource_dir in sorted(p for p in cat_dir.iterdir() if p.is_dir()):
            base = sanitize(resource_dir.name).lower()
            skill_name = base
            # Disambiguate cross-category collisions deterministically.
            if skill_name in used_names:
                skill_name = f"{category.split('-')[0]}-{base}"
            used_names.add(skill_name)

            row = catalog.get(resource_dir.name)
            skill_md, description = make_skill(
                skill_name=skill_name,
                category_label=label,
                resource_dir=resource_dir,
                row=row,
            )

            dest = output / skill_name
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "SKILL.md").write_text(skill_md + "\n", encoding="utf-8")
            # Preserve original files verbatim alongside the skill.
            for f in sorted(p for p in resource_dir.rglob("*") if p.is_file()):
                rel = f.relative_to(resource_dir)
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, target)

            grouped[label].append((skill_name, description))

    _write_catalog(output, grouped)
    total = sum(len(v) for v in grouped.values())
    print(f"Imported {total} community skills into {output}")


def _write_catalog(output: Path, grouped: dict[str, list[tuple[str, str]]]) -> None:
    lines = [
        "# Community Skills",
        "",
        "Claude Code resources curated by",
        "[awesome-claude-code](https://github.com/anthropics/awesome-claude-code), repackaged as",
        "iii-installable skills. Each folder is a standalone skill with a `SKILL.md`; the original",
        "resource files are preserved alongside it.",
        "",
        "## Install",
        "",
        "```bash",
        "# everything",
        "npx skills add iii-hq/iii/community-skills",
        "",
        "# a single skill",
        "npx skills add iii-hq/iii/community-skills --skill commit",
        "```",
        "",
        "## Provenance",
        "",
        "These resources are contributed by their original authors and retain their original",
        "licenses (see each skill's `SKILL.md`). Only open-source-licensed resources are hosted",
        "here, mirroring awesome-claude-code's hosting policy.",
        "",
        "## Catalog",
        "",
    ]
    for label, entries in grouped.items():
        if not entries:
            continue
        lines.append(f"### {SECTION_HEADINGS.get(label, label)}")
        lines.append("")
        for name, desc in sorted(entries):
            short = desc.split(" (")[0]
            lines.append(f"- [`{name}`](./{name}/SKILL.md) — {short}")
        lines.append("")
    (output / "SKILLS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    # README mirrors the catalog header for at-a-glance browsing.
    (output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
