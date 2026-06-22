#!/usr/bin/env python3
"""Import Docker awesome-compose samples as iii scaffolding templates.

Each awesome-compose sample directory (`nginx-golang`, `fastapi`, ...) is
converted into an iii template under `templates/iii/<name>/`:

  - every file in the sample is copied verbatim,
  - a generated `template.yaml` lists those files and marks them all as
    language-agnostic `common` (pattern `*`) so the scaffolder copies them
    regardless of which languages the user selects, and
  - the sample is registered in the root `templates/iii/template.yaml`.

This mirrors the layout the iii scaffolder expects from the templates repo
(`{repo}/iii/template.yaml` + per-template folders), so the generated
directory works directly with:

    iii project init --template <name> --template-dir templates/iii

Usage:
    python scripts/import-compose-templates.py <awesome-compose-dir> \
        [sample ...]

If no sample names are given, the curated default set is imported. Pass
`--all` to import every sample directory found in the source tree.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

# Curated set of lean, self-contained samples that scaffold cleanly. The
# heavier samples (vendored jquery/bootstrap, checked-in package-lock files,
# screenshot galleries) are intentionally left out of the default set; pass
# --all to import everything.
DEFAULT_SAMPLES = [
    "nginx-golang",
    "nginx-golang-postgres",
    "nginx-nodejs-redis",
    "nginx-flask-mysql",
    "fastapi",
    "flask",
    "flask-redis",
    "postgresql-pgadmin",
    "prometheus-grafana",
    "wordpress-mysql",
    "django",
    "spring-postgres",
]

# Files/directories that are never worth importing into a template.
SKIP_DIR_NAMES = {".git", "node_modules", "__pycache__", ".idea", ".vscode"}
SKIP_FILE_SUFFIXES = (
    ".log",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".ico",
    ".min.map",
)
SKIP_FILE_NAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}

MIN_III_VERSION = "0.11.0"

REPO_ROOT = Path(__file__).resolve().parent.parent
DEST_ROOT = REPO_ROOT / "templates" / "iii"


def is_compose_sample(path: Path) -> bool:
    """A sample is any directory that ships a compose file."""
    return path.is_dir() and any(
        (path / name).exists()
        for name in ("compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml")
    )


def should_skip(rel: Path) -> bool:
    if any(part in SKIP_DIR_NAMES for part in rel.parts):
        return True
    if rel.name in SKIP_FILE_NAMES:
        return True
    name = rel.name.lower()
    return any(name.endswith(suffix) for suffix in SKIP_FILE_SUFFIXES)


def collect_files(sample_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(sample_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(sample_dir)
        if should_skip(rel):
            continue
        files.append(rel)
    return files


# `- [`NGINX / Node.js / Redis`](nginx-nodejs-redis) - Sample Node.js ...`
_README_ENTRY = re.compile(
    r"^\s*-\s*\[`(?P<label>[^`]+)`\]\((?P<dir>[^)#]+)\)"
    r"(?:\s*[-–]\s*(?P<desc>.+))?\s*$"
)


def parse_root_readme(source: Path) -> dict[str, tuple[str, str | None]]:
    """Map sample dir -> (label, description) from the awesome-compose index."""
    mapping: dict[str, tuple[str, str | None]] = {}
    readme = source / "README.md"
    if not readme.exists():
        return mapping
    for line in readme.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _README_ENTRY.match(line)
        if not m:
            continue
        target = m.group("dir").strip().strip("/")
        # Link targets are sometimes nested (e.g. official-documentation-samples/...).
        key = target.split("/")[0]
        label = m.group("label").strip()
        desc = m.group("desc")
        mapping.setdefault(key, (label, desc.strip() if desc else None))
    return mapping


def derive_meta(name: str, readme_index: dict[str, tuple[str, str | None]]) -> tuple[str, str]:
    """Return (display_name, description) for a sample.

    The awesome-compose index README is the source of truth: it carries the
    human label (`NGINX / Node.js / Redis`) and a one-line description. The
    per-sample READMEs are boilerplate ("Compose sample application"), so they
    are not used. Falls back to a title-cased directory name when the sample
    is absent from the index.
    """
    label, desc = readme_index.get(name, (None, None))
    display = label or name.replace("-", " ").replace("_", " ").title()
    description = desc or f"Docker Compose sample stack ({display}) from awesome-compose."
    # YAML-safe single-line strings.
    return display.replace('"', "'"), description.replace('"', "'")


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_template_yaml(display: str, description: str, files: list[Path]) -> str:
    lines = [
        f"name: {yaml_quote(display)}",
        f"description: {yaml_quote(description)}",
        'version: "0.1.0"',
        f'min_iii_version: "{MIN_III_VERSION}"',
        "",
        "# Compose samples are language-agnostic from the scaffolder's point of",
        "# view: the Dockerfiles own the per-language build. No language gating.",
        "treat_required_as_included: true",
        "requires: []",
        "optional: []",
        "",
        "# Mark every bundled file as 'common' so the scaffolder copies the whole",
        "# stack regardless of which languages the user selects.",
        "language_files:",
        "  common:",
        "    - '*'",
        "",
        "files:",
    ]
    for rel in files:
        lines.append(f"  - {yaml_quote(rel.as_posix())}")
    lines += [
        "",
        "next_steps:",
        '  - "Start the stack: docker compose up"',
        '  - "Stop and remove it: docker compose down"',
    ]
    return "\n".join(lines) + "\n"


def import_sample(
    source: Path, name: str, readme_index: dict[str, tuple[str, str | None]]
) -> bool:
    sample_dir = source / name
    if not is_compose_sample(sample_dir):
        print(f"  skip {name}: not a compose sample", file=sys.stderr)
        return False

    files = collect_files(sample_dir)
    if not files:
        print(f"  skip {name}: no importable files", file=sys.stderr)
        return False

    dest_dir = DEST_ROOT / name
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    for rel in files:
        dest = dest_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sample_dir / rel, dest)

    display, description = derive_meta(name, readme_index)
    (dest_dir / "template.yaml").write_text(
        render_template_yaml(display, description, files), encoding="utf-8"
    )
    print(f"  imported {name}: {len(files)} files -> {dest_dir.relative_to(REPO_ROOT)}")
    return True


def render_root_yaml(names: list[str]) -> str:
    lines = [
        "# Root template manifest for the iii compose-sample store.",
        "#",
        "# Generated by scripts/import-compose-templates.py from Docker's",
        "# awesome-compose samples. Use with:",
        "#",
        "#   iii project init --template <name> --template-dir templates/iii",
        "#",
        "templates:",
    ]
    lines += [f"  - {name}" for name in names]
    lines += [
        "",
        "# Root-level language file patterns. Individual compose templates override",
        "# these with `common: ['*']`, so this mainly documents the stack file types.",
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
        "    - 'LICENSE'",
        "    - '.env'",
        "    - '.env.*'",
        "    - '.gitignore'",
        "    - '.dockerignore'",
    ]
    return "\n".join(lines) + "\n"


def existing_templates() -> list[str]:
    """Names already present on disk (each dir with a template.yaml)."""
    if not DEST_ROOT.exists():
        return []
    return sorted(
        p.name
        for p in DEST_ROOT.iterdir()
        if p.is_dir() and (p / "template.yaml").exists()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Path to an awesome-compose checkout")
    parser.add_argument("samples", nargs="*", help="Sample directory names to import")
    parser.add_argument(
        "--all", action="store_true", help="Import every compose sample in the source tree"
    )
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    if not source.is_dir():
        print(f"error: source directory not found: {source}", file=sys.stderr)
        return 1

    if args.all:
        samples = sorted(p.name for p in source.iterdir() if is_compose_sample(p))
    elif args.samples:
        samples = args.samples
    else:
        samples = DEFAULT_SAMPLES

    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"Importing {len(samples)} sample(s) into {DEST_ROOT.relative_to(REPO_ROOT)}")

    readme_index = parse_root_readme(source)
    imported = [name for name in samples if import_sample(source, name, readme_index)]
    if not imported:
        print("error: nothing imported", file=sys.stderr)
        return 1

    # Re-derive the registered list from disk so the root manifest always
    # reflects reality even across partial re-runs.
    names = existing_templates()
    (DEST_ROOT / "template.yaml").write_text(render_root_yaml(names), encoding="utf-8")
    print(f"Wrote root manifest with {len(names)} template(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
