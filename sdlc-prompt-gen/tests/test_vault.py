"""Vault 保存・検索のユニットテスト。"""

from __future__ import annotations

from datetime import datetime

from sdlc_prompt_gen.vault.store import retrieve_context, save_artifact, slugify


def test_slugify_keeps_japanese_and_lowercases():
    assert slugify("ECサイト") == "ecサイト"
    assert slugify("  Hello World!  ") == "hello-world"
    assert slugify("///") == "untitled"


def test_save_artifact_path_and_frontmatter(monkeypatch, tmp_path):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    result = save_artifact(
        phase=3,
        title="ECサイト",
        content="本文です",
        project="ec-demo",
        now=datetime(2026, 6, 24, 10, 0, 0),
    )
    assert result.relative == "prompts/2026/06/3-ecサイト.md"
    saved = (tmp_path / result.relative).read_text(encoding="utf-8")
    assert saved.startswith("---")
    assert "phase: 3" in saved
    assert "本文です" in saved


def test_retrieve_context_ranks_by_match(monkeypatch, tmp_path):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    save_artifact(3, "認証設計", "ログイン 認証 トークン", "p", now=datetime(2026, 6, 1))
    save_artifact(3, "決済設計", "支払い 決済", "p", now=datetime(2026, 6, 2))
    hits = retrieve_context("認証 ログイン", limit=5)
    assert hits, "少なくとも1件ヒットするはず"
    assert "認証" in hits[0]["preview"]
