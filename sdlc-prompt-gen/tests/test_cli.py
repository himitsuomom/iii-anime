"""server.main の CLI 引数処理のテスト（mcp.run を呼ばずに終了すること）。"""

from __future__ import annotations

import pytest

pytest.importorskip("mcp", reason="mcp 未インストール環境では server のインポートをスキップ")

from sdlc_prompt_gen.server import main  # noqa: E402


def test_help_returns_zero(capsys):
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    assert "sdlc-prompt-gen" in out
    assert "VAULT_PATH" in out


def test_version_returns_zero(capsys):
    assert main(["--version"]) == 0
    assert "sdlc-prompt-gen" in capsys.readouterr().out


def test_unknown_arg_returns_two():
    assert main(["--frobnicate"]) == 2
