#!/usr/bin/env python3
"""Import curated "awesome-list" GitHub repos as iii reference templates.

Each list repo (awesome-python, awesome-go, ...) becomes a *reference /
knowledge-pack* template under `templates/iii/<name>/`:

  - `RESOURCES.md` — the curated upstream README, prefixed with an attribution
    header (source, license, snapshot note),
  - `index.yaml` — a structured index extracted from the README's `##`/`###`
    headings (categories the list covers), and
  - `template.yaml` — a manifest whose `selection` metadata makes the list
    discoverable by `iii project init --intent "..."`.

Unlike the Docker Compose stacks (see `import-compose-templates.py`), these are
docs-only: `requires_docker: false`, no language gating, all files marked
`common: ['*']`. They are tagged `kind:reference` so the catalog can tell the
two kinds apart, and their tags are resource-oriented (`lang:python`,
`topic:security`, …) rather than stack-capability tags, so stack-building
intents keep matching the compose templates.

Usage:
    python scripts/import-awesome-lists.py                 # curated default set
    python scripts/import-awesome-lists.py vinta/awesome-python avelino/awesome-go

The REPOS table below is the single place to add new lists.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

MIN_III_VERSION = "0.11.0"
REPO_ROOT = Path(__file__).resolve().parent.parent
DEST_ROOT = REPO_ROOT / "templates" / "iii"

# Tags every reference template carries (distinguishes them from compose stacks).
BASE_TAGS = ["kind:reference", "awesome", "docs"]

# Headings that are navigation/boilerplate, not real content categories.
SKIP_HEADINGS = {
    "contents",
    "table of contents",
    "toc",
    "index",
    "sponsors",
    "sponsor",
    "contributing",
    "contribution",
    "contributors",
    "license",
    "licence",
    "legal",
    "about",
    "acknowledgements",
    "acknowledgments",
    "credits",
    "thanks",
    "footnotes",
    "anti-features",
}

# Curated catalog. `domain` drives orchestration quality; everything else is
# fetched/derived. `template` defaults to the repo name lowercased.
REPOS: list[dict] = [
    {
        "repo": "sindresorhus/awesome",
        "domain": {
            "summary": "A curated meta-list of awesome lists across every topic",
            "tags": ["meta", "topic:index"],
            "keywords": ["awesome", "list", "curated", "meta", "directory", "index"],
        },
    },
    {
        "repo": "vinta/awesome-python",
        "domain": {
            "summary": "Curated Python frameworks, libraries, software, and resources",
            "tags": ["lang:python", "topic:libraries"],
            "keywords": ["python", "django", "flask", "async", "scraping", "data", "web"],
        },
    },
    {
        "repo": "awesome-selfhosted/awesome-selfhosted",
        "domain": {
            "summary": "Self-hosted software you can run on your own server",
            "tags": ["topic:selfhosted", "topic:devops"],
            "keywords": ["self-hosted", "selfhosted", "server", "homelab", "privacy", "foss"],
        },
    },
    {
        "repo": "trimstray/the-book-of-secret-knowledge",
        "template": "book-of-secret-knowledge",
        "domain": {
            "summary": "Sysadmin, security, networking, and hacking tools, cheatsheets, and knowledge",
            "tags": ["topic:security", "topic:sysadmin", "topic:networking"],
            "keywords": ["security", "sysadmin", "networking", "devops", "cheatsheet", "cli", "hacking"],
        },
    },
    {
        "repo": "avelino/awesome-go",
        "domain": {
            "summary": "Curated Go frameworks, libraries, and software",
            "tags": ["lang:go", "topic:libraries"],
            "keywords": ["go", "golang", "microservices", "cli", "web", "backend"],
        },
    },
    {
        "repo": "521xueweihan/HelloGitHub",
        "template": "hellogithub",
        "domain": {
            "summary": "Interesting, beginner-friendly open source projects",
            "tags": ["topic:opensource", "topic:projects"],
            "keywords": ["opensource", "github", "projects", "beginner"],
        },
    },
    {
        "repo": "Hack-with-Github/Awesome-Hacking",
        "template": "awesome-hacking",
        "domain": {
            "summary": "Curated hacking, pentest, and offensive security resources",
            "tags": ["topic:security", "topic:hacking"],
            "keywords": ["hacking", "pentest", "security", "ctf", "exploit", "redteam", "osint"],
        },
    },
    {
        "repo": "papers-we-love/papers-we-love",
        "domain": {
            "summary": "Academic computer science papers worth reading",
            "tags": ["topic:papers", "topic:computer-science"],
            "keywords": ["papers", "research", "academic", "algorithms", "distributed-systems"],
        },
    },
    {
        "repo": "jaywcjlove/awesome-mac",
        "domain": {
            "summary": "Great macOS applications and tools",
            "tags": ["platform:mac", "topic:apps"],
            "keywords": ["mac", "macos", "apps", "applications", "productivity", "software"],
        },
    },
    {
        "repo": "enaqx/awesome-react",
        "domain": {
            "summary": "React ecosystem: tutorials, tools, and resources",
            "tags": ["lang:javascript", "framework:react", "topic:frontend"],
            "keywords": ["react", "javascript", "frontend", "hooks", "redux", "ecosystem"],
        },
    },
    {
        "repo": "fffaraz/awesome-cpp",
        "domain": {
            "summary": "Curated C++ frameworks, libraries, and resources",
            "tags": ["lang:cpp", "topic:libraries"],
            "keywords": ["cpp", "c++", "libraries", "frameworks", "systems"],
        },
    },
    {
        "repo": "binhnguyennus/awesome-scalability",
        "domain": {
            "summary": "Scalability, system design, and high-performance backend patterns",
            "tags": ["topic:scalability", "topic:system-design", "topic:architecture"],
            "keywords": ["scalability", "system-design", "architecture", "distributed", "performance", "backend"],
        },
    },
    {
        "repo": "sindresorhus/awesome-nodejs",
        "domain": {
            "summary": "Curated Node.js packages and resources",
            "tags": ["lang:javascript", "runtime:node", "topic:libraries"],
            "keywords": ["node", "nodejs", "javascript", "npm", "backend", "packages"],
        },
    },
    {
        "repo": "Solido/awesome-flutter",
        "domain": {
            "summary": "Flutter resources, packages, components, and apps",
            "tags": ["framework:flutter", "lang:dart", "topic:mobile"],
            "keywords": ["flutter", "dart", "mobile", "cross-platform", "widgets"],
        },
    },
    {
        "repo": "tiimgreen/github-cheat-sheet",
        "domain": {
            "summary": "Cool Git and GitHub features, tips, and tricks",
            "tags": ["topic:git", "topic:cheatsheet"],
            "keywords": ["git", "github", "cheatsheet", "version-control", "tips"],
        },
    },
    {
        "repo": "wasabeef/awesome-android-ui",
        "domain": {
            "summary": "Awesome Android UI libraries and components",
            "tags": ["platform:android", "topic:ui"],
            "keywords": ["android", "ui", "mobile", "components", "animation"],
        },
    },
    {
        "repo": "vsouza/awesome-ios",
        "domain": {
            "summary": "Curated iOS libraries, frameworks, and resources",
            "tags": ["platform:ios", "lang:swift", "topic:mobile"],
            "keywords": ["ios", "swift", "objective-c", "mobile", "cocoa", "libraries"],
        },
    },
    {
        "repo": "dkhamsing/open-source-ios-apps",
        "domain": {
            "summary": "Open source iOS apps",
            "tags": ["platform:ios", "topic:apps", "topic:opensource"],
            "keywords": ["ios", "apps", "swift", "opensource", "iphone"],
        },
    },
    {
        "repo": "serhii-londar/open-source-mac-os-apps",
        "domain": {
            "summary": "Open source macOS apps",
            "tags": ["platform:mac", "topic:apps", "topic:opensource"],
            "keywords": ["mac", "macos", "apps", "opensource", "swift"],
        },
    },
    {
        "repo": "akullpp/awesome-java",
        "domain": {
            "summary": "Curated Java frameworks, libraries, and software",
            "tags": ["lang:java", "topic:libraries"],
            "keywords": ["java", "jvm", "spring", "libraries", "frameworks"],
        },
    },
    {
        "repo": "brillout/awesome-react-components",
        "domain": {
            "summary": "Curated React component libraries",
            "tags": ["lang:javascript", "framework:react", "topic:frontend", "topic:components"],
            "keywords": ["react", "components", "ui", "frontend", "libraries"],
        },
    },
    {
        "repo": "DovAmir/awesome-design-patterns",
        "domain": {
            "summary": "Software design and architecture patterns",
            "tags": ["topic:design-patterns", "topic:architecture"],
            "keywords": ["design-patterns", "architecture", "oop", "software-design", "patterns"],
        },
    },
]

# License markers -> SPDX-ish label.
LICENSE_MARKERS = [
    ("CC0 1.0", "CC0-1.0"),
    ("CC0-1.0", "CC0-1.0"),
    ("Attribution-ShareAlike", "CC-BY-SA"),
    ("CC-BY-SA", "CC-BY-SA"),
    ("Attribution 4.0", "CC-BY-4.0"),
    ("CC BY 4.0", "CC-BY-4.0"),
    ("CC-BY", "CC-BY"),
    ("Creative Commons", "Creative Commons"),
    ("MIT License", "MIT"),
    ("The MIT License", "MIT"),
    ("Apache License", "Apache-2.0"),
    ("Mozilla Public License", "MPL-2.0"),
    ("GNU GENERAL PUBLIC", "GPL"),
    ("Unlicense", "Unlicense"),
]


def curl(url: str) -> str | None:
    """Fetch a URL via curl (works through this env's HTTPS proxy). Returns
    decoded text on HTTP 200, else None."""
    try:
        proc = subprocess.run(
            ["curl", "-fsSL", url],
            capture_output=True,
            timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", errors="replace")


def fetch_readme(repo: str) -> tuple[str, str] | None:
    """Return (url, text) for the first reachable README, trying common
    branch/filename combinations."""
    for branch in ("main", "master"):
        for fn in ("README.md", "readme.md", "Readme.md"):
            url = f"https://raw.githubusercontent.com/{repo}/{branch}/{fn}"
            text = curl(url)
            if text is not None:
                return url, text
    return None


def detect_license(repo: str) -> str:
    for branch in ("main", "master"):
        for fn in ("LICENSE", "LICENSE.md", "license", "license.md", "LICENSE.txt", "COPYING"):
            text = curl(f"https://raw.githubusercontent.com/{repo}/{branch}/{fn}")
            if not text:
                continue
            head = text[:4000]
            for marker, label in LICENSE_MARKERS:
                if marker.lower() in head.lower():
                    return label
            return "See source repository"
    return "See source repository"


_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_BARE_URL = re.compile(r"\(?https?://\S+\)?")
_EMOJI_PREFIX = re.compile(r"^[^\w(]+")
_HTML_TAG = re.compile(r"<[^>]+>")
_ANCHOR = re.compile(r"\{#[^}]*\}")


def clean_heading(text: str) -> str:
    """Strip markdown images/links/badges, html, anchors, and leading emoji."""
    text = _IMAGE.sub("", text)
    # Collapse links to their label; run twice for nested `[![...](...)](...)`.
    text = _LINK.sub(r"\1", text)
    text = _LINK.sub(r"\1", text)
    text = _IMAGE.sub("", text)
    text = _HTML_TAG.sub("", text)
    text = _ANCHOR.sub("", text)
    text = _BARE_URL.sub("", text)
    text = text.replace("*", "").replace("`", "").replace("[", "").replace("]", "")
    text = _EMOJI_PREFIX.sub("", text)
    return re.sub(r"\s+", " ", text).strip(" -–—:|")


def _title_from_slug(repo: str) -> str:
    slug = repo.split("/")[-1]
    return " ".join(w.capitalize() for w in re.split(r"[-_]", slug) if w)


def extract_title(readme: str, repo: str) -> str:
    for line in readme.splitlines():
        s = line.strip()
        if s.startswith("# "):
            t = clean_heading(s[2:])
            # Reject titles that cleaned down to noise (badge-only H1s).
            if t and len(t) > 1 and not t.lower().startswith("http"):
                return t
    return _title_from_slug(repo)


def extract_categories(readme: str) -> list[dict]:
    """Parse markdown headings into [{name, subcategories: [...]}], skipping
    boilerplate and fenced code. The "category" level is the shallowest heading
    level present (some lists use `##`, others jump straight to `###`); the next
    level down becomes subcategories. Caps sizes to keep index.yaml reasonable."""
    # First pass: collect non-boilerplate headings at levels 2-4.
    headings: list[tuple[int, str]] = []
    in_code = False
    for line in readme.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r"^(#{2,4})\s+(.*)$", line)
        if not m:
            continue
        name = clean_heading(m.group(2))
        if not name or name.lower() in SKIP_HEADINGS:
            continue
        headings.append((len(m.group(1)), name))

    if not headings:
        return []

    cat_level = min(level for level, _ in headings)
    sub_level = cat_level + 1

    categories: list[dict] = []
    current: dict | None = None
    for level, name in headings:
        if level == cat_level:
            current = {"name": name, "subcategories": []}
            categories.append(current)
        elif level == sub_level and current is not None:
            if len(current["subcategories"]) < 30:
                current["subcategories"].append(name)
    return categories[:80]


def _dedupe(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in seq:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _yaml_list(key: str, values: list[str], indent: str = "  ") -> list[str]:
    if not values:
        return [f"{indent}{key}: []"]
    out = [f"{indent}{key}:"]
    out += [f"{indent}  - {yaml_quote(v)}" for v in values]
    return out


def render_index_yaml(
    source: str, title: str, license_label: str, categories: list[dict]
) -> str:
    lines = [
        "# Structured index of the curated list, extracted from its README",
        "# headings by scripts/import-awesome-lists.py.",
        f"source: {yaml_quote(source)}",
        f"title: {yaml_quote(title)}",
        f"license: {yaml_quote(license_label)}",
        f"category_count: {len(categories)}",
        "categories:",
    ]
    if not categories:
        lines.append("  []")
    for cat in categories:
        lines.append(f"  - name: {yaml_quote(cat['name'])}")
        subs = cat["subcategories"]
        if subs:
            lines.append("    subcategories:")
            lines += [f"      - {yaml_quote(s)}" for s in subs]
        else:
            lines.append("    subcategories: []")
    return "\n".join(lines) + "\n"


def render_resources_md(
    repo: str, source: str, license_label: str, readme: str
) -> str:
    header = (
        f"<!-- Imported by scripts/import-awesome-lists.py -->\n"
        f"> **Source:** [{repo}]({source})  \n"
        f"> **License:** {license_label}  \n"
        f"> This is a snapshot of the upstream README. Visit the source for the "
        f"latest version and to contribute.\n\n---\n\n"
    )
    return header + readme.rstrip() + "\n"


def render_template_yaml(
    display: str,
    description: str,
    source: str,
    license_label: str,
    tags: list[str],
    keywords: list[str],
    use_cases: list[str],
) -> str:
    lines = [
        f"name: {yaml_quote(display)}",
        f"description: {yaml_quote(description)}",
        'version: "0.1.0"',
        f'min_iii_version: "{MIN_III_VERSION}"',
        "",
        "# Reference / knowledge-pack template: docs-only, language-agnostic.",
        "treat_required_as_included: true",
        "requires: []",
        "optional: []",
        "",
        "# Copy every bundled file regardless of language selection.",
        "language_files:",
        "  common:",
        "    - '*'",
        "",
        "# Selection metadata for intent-based orchestration.",
        "# 使用する場面 / 使用条件. Tagged kind:reference (no Docker, no stack).",
        "selection:",
    ]
    lines += _yaml_list("use_cases", use_cases)
    lines += _yaml_list("tags", tags)
    lines += _yaml_list("keywords", keywords)
    lines += [
        "  conditions:",
        "    requires_docker: false",
        "    services: []",
    ]
    lines += _yaml_list(
        "notes",
        [
            f"Source: {source}",
            f"License: {license_label}",
            "Curated link list — snapshot of the upstream README.",
        ],
        indent="    ",
    )
    lines += [
        "",
        "files:",
        '  - "RESOURCES.md"',
        '  - "index.yaml"',
        "",
        "next_steps:",
        '  - "Browse the curated list in RESOURCES.md"',
        '  - "See index.yaml for the categories it covers"',
        f'  - "Source: {source}"',
    ]
    return "\n".join(lines) + "\n"


def import_repo(spec: dict) -> bool:
    repo = spec["repo"]
    name = spec.get("template", repo.split("/")[-1].lower())
    domain = spec.get("domain", {})

    fetched = fetch_readme(repo)
    if not fetched:
        print(f"  skip {repo}: README not reachable", file=sys.stderr)
        return False
    source = f"https://github.com/{repo}"
    _, readme = fetched
    license_label = detect_license(repo)
    title = extract_title(readme, repo)
    categories = extract_categories(readme)

    display = title
    description = domain.get("summary") or f"Curated list from {repo}"

    tags = _dedupe(BASE_TAGS + domain.get("tags", []))
    category_tokens = _dedupe(
        tok
        for cat in categories
        for tok in re.split(r"[^a-z0-9+]+", cat["name"].lower())
        if len(tok) > 2
    )
    repo_tokens = [t for t in re.split(r"[^a-z0-9+]+", name.lower()) if len(t) > 1]
    keywords = _dedupe(
        domain.get("keywords", []) + repo_tokens + category_tokens[:25]
    )
    use_cases = _dedupe(
        [
            description,
            f"Find curated {title} resources, libraries, and tools",
            f"Reference list / knowledge pack for {title}",
        ]
    )

    dest = DEST_ROOT / name
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "RESOURCES.md").write_text(
        render_resources_md(repo, source, license_label, readme), encoding="utf-8"
    )
    (dest / "index.yaml").write_text(
        render_index_yaml(source, title, license_label, categories), encoding="utf-8"
    )
    (dest / "template.yaml").write_text(
        render_template_yaml(
            display, description, source, license_label, tags, keywords, use_cases
        ),
        encoding="utf-8",
    )
    print(
        f"  imported {name}: {len(categories)} categories, license={license_label} "
        f"-> {dest.relative_to(REPO_ROOT)}"
    )
    return True


def registered_templates() -> list[str]:
    if not DEST_ROOT.exists():
        return []
    return sorted(
        p.name
        for p in DEST_ROOT.iterdir()
        if p.is_dir() and (p / "template.yaml").exists()
    )


def render_root_yaml(names: list[str]) -> str:
    lines = [
        "# Root template manifest for the iii template store.",
        "#",
        "# Holds two kinds of templates, both intent-orchestrated:",
        "#   - Docker Compose stacks (scripts/import-compose-templates.py)",
        "#   - Reference / knowledge packs from awesome-lists",
        "#     (scripts/import-awesome-lists.py)",
        "#",
        "#   iii project init --template <name> --template-dir templates/iii",
        "#   iii project init --intent \"...\"     --template-dir templates/iii",
        "#",
        "templates:",
    ]
    lines += [f"  - {name}" for name in names]
    lines += [
        "",
        "# Root-level language file patterns. Per-template manifests override",
        "# these with `common: ['*']`.",
        "language_files:",
        "  common:",
        "    - 'compose.yaml'",
        "    - 'compose.yml'",
        "    - 'docker-compose.yml'",
        "    - 'docker-compose.*.yml'",
        "    - 'Dockerfile'",
        "    - '*.conf'",
        "    - 'README.md'",
        "    - 'README*'",
        "    - 'RESOURCES.md'",
        "    - 'index.yaml'",
        "    - 'LICENSE'",
        "    - '.env'",
        "    - '.env.*'",
        "    - '.gitignore'",
        "    - '.dockerignore'",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "repos",
        nargs="*",
        help="owner/name repos to import (default: the curated REPOS table)",
    )
    args = parser.parse_args()

    if args.repos:
        wanted = set(args.repos)
        specs = [s for s in REPOS if s["repo"] in wanted]
        # Allow importing a repo not in the table (no curated domain metadata).
        known = {s["repo"] for s in REPOS}
        specs += [{"repo": r} for r in args.repos if r not in known]
    else:
        specs = REPOS

    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"Importing {len(specs)} awesome-list(s) into {DEST_ROOT.relative_to(REPO_ROOT)}")

    imported = [s["repo"] for s in specs if import_repo(s)]
    if not imported:
        print("error: nothing imported", file=sys.stderr)
        return 1

    names = registered_templates()
    (DEST_ROOT / "template.yaml").write_text(render_root_yaml(names), encoding="utf-8")
    print(f"Wrote root manifest with {len(names)} template(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
