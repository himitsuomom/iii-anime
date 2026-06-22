"""Unit tests for the skills catalog tooling.

Covers _skills_lib frontmatter parsing, audit_skills invariant rules,
build_skills_catalog output, and check_skills_docs drift detection.

Run with: python -m pytest .github/scripts/test_skills_catalog.py -v
"""
from __future__ import annotations

from pathlib import Path

import pytest

import audit_skills
import build_skills_catalog
import check_skills_docs
from _skills_lib import parse_frontmatter, read_h1


# ── frontmatter parsing ────────────────────────────────────────────────
class TestParseFrontmatter:
    def test_none_without_block(self):
        assert parse_frontmatter("# just a doc\n") is None

    def test_bare_and_quoted(self):
        meta = parse_frontmatter('---\nname: iii-x\ntitle: "Hi"\n---\nbody\n')
        assert meta == {"name": "iii-x", "title": "Hi"}

    def test_folded_block_scalar(self):
        text = (
            "---\n"
            "name: iii-core\n"
            "description: >-\n"
            "  first line\n"
            "  second line\n"
            "---\n"
            "# Body\n"
        )
        meta = parse_frontmatter(text)
        assert meta["name"] == "iii-core"
        assert meta["description"] == "first line second line"

    def test_literal_block_scalar_keeps_newlines(self):
        text = "---\nnote: |\n  a\n  b\n---\nx\n"
        meta = parse_frontmatter(text)
        assert meta["note"] == "a\nb"

    def test_inline_list(self):
        meta = parse_frontmatter('---\ntags: [a, "b", c]\n---\nx\n')
        assert meta["tags"] == ["a", "b", "c"]

    def test_read_h1(self):
        assert read_h1("intro\n# Title here\nmore\n") == "Title here"
        assert read_h1("no heading\n") is None


# ── fixtures ────────────────────────────────────────────────────────────
def _make_skill(skills_dir: Path, name: str, *, description: str = "Use when testing things.",
                title: str = "Demo Skill", frontmatter_name: str | None = None,
                body_filler: str = "x" * 500) -> Path:
    fm_name = name if frontmatter_name is None else frontmatter_name
    skill = skills_dir / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {fm_name}\ndescription: >-\n  {description}\n---\n\n# {title}\n\n{body_filler}\n",
        encoding="utf-8",
    )
    return skill


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    d = tmp_path / "skills"
    d.mkdir()
    _make_skill(d, "iii-alpha")
    _make_skill(d, "iii-beta")
    (d / "README.md").write_text("# Skills\n- iii-alpha\n- iii-beta\n", encoding="utf-8")
    (d / "SKILLS.md").write_text("Catalog: iii-alpha, iii-beta\n", encoding="utf-8")
    return d


# ── audit_skills ────────────────────────────────────────────────────────
class TestAudit:
    def test_clean(self, skills_dir: Path):
        audit = audit_skills.run_audit(skills_dir)
        assert audit.skills_checked == 2
        assert audit.issues == []

    def test_bad_folder_name(self, skills_dir: Path):
        _make_skill(skills_dir, "iii-Bad_Name")
        audit = audit_skills.run_audit(skills_dir)
        assert any(i.rule == "S001" for i in audit.issues)

    def test_missing_skill_md(self, skills_dir: Path):
        (skills_dir / "iii-gamma").mkdir()
        audit = audit_skills.run_audit(skills_dir)
        assert any(i.rule == "S002" for i in audit.issues)

    def test_name_mismatch(self, skills_dir: Path):
        _make_skill(skills_dir, "iii-delta", frontmatter_name="iii-wrong")
        audit = audit_skills.run_audit(skills_dir)
        assert any(i.rule == "S004" for i in audit.issues)

    def test_missing_h1(self, skills_dir: Path):
        skill = skills_dir / "iii-epsilon"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "---\nname: iii-epsilon\ndescription: >-\n  hi there friend\n---\n\nno heading "
            + "x" * 500,
            encoding="utf-8",
        )
        audit = audit_skills.run_audit(skills_dir)
        assert any(i.rule == "S005" for i in audit.issues)

    def test_too_short(self, skills_dir: Path):
        _make_skill(skills_dir, "iii-zeta", body_filler="short")
        audit = audit_skills.run_audit(skills_dir)
        assert any(i.rule == "S006" for i in audit.issues)

    def test_broken_internal_link(self, skills_dir: Path):
        skill = skills_dir / "iii-eta"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "---\nname: iii-eta\ndescription: >-\n  hi there friend\n---\n\n# Eta\n\n"
            "[broken](./missing.md)\n" + "x" * 500,
            encoding="utf-8",
        )
        audit = audit_skills.run_audit(skills_dir)
        assert any(i.rule == "S007" for i in audit.issues)

    def test_not_in_catalog_docs(self, skills_dir: Path):
        _make_skill(skills_dir, "iii-theta")  # not added to README/SKILLS
        audit = audit_skills.run_audit(skills_dir)
        assert any(i.rule == "S008" and "iii-theta" in i.message for i in audit.issues)


# ── build_skills_catalog ──────────────────────────────────────────────────
class TestBuildCatalog:
    def test_shape(self, skills_dir: Path):
        catalog = build_skills_catalog.build_catalog(skills_dir)
        assert catalog["schema_version"] == 1
        assert catalog["totals"]["skills"] == 2
        names = [s["name"] for s in catalog["skills"]]
        assert names == ["iii-alpha", "iii-beta"]
        first = catalog["skills"][0]
        assert first["title"] == "Demo Skill"
        assert first["description"].startswith("Use when")
        assert first["bytes"] > 0

    def test_slug_to_title(self):
        assert build_skills_catalog.slug_to_title("iii-core-primitives") == "Core Primitives"

    def test_serialize_roundtrip(self, skills_dir: Path):
        catalog = build_skills_catalog.build_catalog(skills_dir)
        import json

        assert json.loads(build_skills_catalog.serialize(catalog)) == catalog


# ── check_skills_docs ─────────────────────────────────────────────────────
class TestCheckDocs:
    def _catalog(self, skills_dir: Path) -> Path:
        catalog = build_skills_catalog.build_catalog(skills_dir)
        out = skills_dir / "catalog.json"
        out.write_text(build_skills_catalog.serialize(catalog), encoding="utf-8")
        return out

    def test_in_sync(self, skills_dir: Path):
        names = check_skills_docs.load_catalog_names(self._catalog(skills_dir))
        assert check_skills_docs.find_drift(skills_dir, names) == []

    def test_missing_listing(self, skills_dir: Path):
        _make_skill(skills_dir, "iii-omega")
        names = check_skills_docs.load_catalog_names(self._catalog(skills_dir))
        drift = check_skills_docs.find_drift(skills_dir, names)
        assert any(d.kind == "missing" and d.skill == "iii-omega" for d in drift)

    def test_stale_reference(self, skills_dir: Path):
        catalog_path = self._catalog(skills_dir)
        (skills_dir / "README.md").write_text(
            "# Skills\n- iii-alpha\n- iii-beta\n- iii-ghost\n", encoding="utf-8"
        )
        names = check_skills_docs.load_catalog_names(catalog_path)
        drift = check_skills_docs.find_drift(skills_dir, names)
        assert any(d.kind == "stale" and d.skill == "iii-ghost" for d in drift)
