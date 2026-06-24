#!/usr/bin/env python3
"""Generate skills/index.json — a flat catalog of every skill under skills/.

Scans each skills/<name>/SKILL.md, reads its YAML frontmatter, and emits a
single index file so agents and tools can list every skill (name, description,
domain, path) without opening 700+ files. Run after adding or editing skills:

    python scripts/generate-skills-index.py

Requires PyYAML (already a dev dependency of the Python SDK).
"""
import json
import os
import sys
import datetime

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO_ROOT, "skills")
OUTPUT = os.path.join(SKILLS_DIR, "index.json")


def read_frontmatter(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].lstrip("\n")
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def domain_for(name, fm):
    if fm.get("domain"):
        return fm["domain"]
    return "iii" if name.startswith("iii-") else "unknown"


def main():
    entries = []
    for name in sorted(os.listdir(SKILLS_DIR)):
        skill_md = os.path.join(SKILLS_DIR, name, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue
        fm = read_frontmatter(skill_md)
        if not fm or not fm.get("name") or not fm.get("description"):
            print(f"WARN: skipping {name} (missing name/description)", file=sys.stderr)
            continue
        entries.append(
            {
                "name": str(fm["name"]).strip(),
                "description": " ".join(str(fm["description"]).split()),
                "domain": domain_for(name, fm),
                "path": f"skills/{name}",
            }
        )

    index = {
        "version": "1.0.0",
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "repository": "https://github.com/iii-hq/iii",
        "total_skills": len(entries),
        "skills": entries,
    }

    with open(OUTPUT, "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"Wrote {OUTPUT} with {len(entries)} skills")


if __name__ == "__main__":
    main()
