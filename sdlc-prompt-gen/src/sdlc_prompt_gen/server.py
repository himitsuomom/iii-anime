"""sdlc-prompt-gen MCP サーバー本体。

公開ツール（4種）:
- ``generate_prompt``      : フェーズのプロンプトを生成
- ``save_artifact``        : 成果物を Vault に保存
- ``retrieve_wiki_context``: 過去ドキュメントを検索
- ``detect_phase``         : 自由文からフェーズを推定

CLI:
- 引数なし        : stdio で MCP サーバーを起動
- ``--help/-h``   : 使い方を表示して終了
- ``--version/-V``: バージョンを表示して終了

注意: ``mcp.run()`` は ``--help`` を解釈せずサーバー待ち受けに入ってしまうため、
``main()`` 側で先に引数を捌いてから ``mcp.run()`` に渡す。
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from sdlc_prompt_gen import __version__
from sdlc_prompt_gen.detect.phase_detector import detect_phase as _detect_phase
from sdlc_prompt_gen.generators.builder import build_prompt
from sdlc_prompt_gen.phases import get_phase
from sdlc_prompt_gen.vault.store import retrieve_context
from sdlc_prompt_gen.vault.store import save_artifact as _save_artifact

mcp = FastMCP("sdlc-prompt-gen")


@mcp.tool()
def generate_prompt(
    phase: int,
    project_context: str,
    response_format: str = "detailed",
    prior_artifacts: list[str] | None = None,
) -> dict:
    """指定フェーズの system_prompt / user_prompt を生成する。

    Args:
        phase: 1..10 の SDLC フェーズ番号。
        project_context: プロジェクト概要やこのフェーズの入力コンテキスト。
        response_format: "detailed"（既定）または "concise"。
        prior_artifacts: 参照すべき既存成果物のパス一覧（任意）。
    """
    spec = get_phase(phase)
    return build_prompt(
        spec,
        project_context=project_context,
        response_format=response_format,
        prior_artifacts=prior_artifacts,
    )


@mcp.tool()
def save_artifact(phase: int, title: str, content: str, project: str = "") -> dict:
    """生成した成果物を Vault に保存し、保存先パスを返す。

    保存規約: ``{VAULT_PATH}/prompts/YYYY/MM/{phase}-{slug}.md``
    """
    result = _save_artifact(phase=phase, title=title, content=content, project=project)
    return {"path": result.path, "relative": result.relative}


@mcp.tool()
def retrieve_wiki_context(query: str, limit: int = 5) -> list[dict]:
    """Vault 内の過去ドキュメントを検索して最大 ``limit`` 件返す。"""
    return retrieve_context(query=query, limit=limit)


@mcp.tool()
def detect_phase(text: str) -> dict:
    """自由文から最も近い SDLC フェーズと確信度を推定する。"""
    result = _detect_phase(text)
    return {
        "phase": result.phase,
        "confidence": result.confidence,
        "matched": result.matched,
    }


_USAGE = """sdlc-prompt-gen — SDLC 10フェーズのプロンプト生成 MCP サーバー

使い方:
  sdlc-prompt-gen              MCP サーバーを stdio で起動（Claude Code から利用）
  sdlc-prompt-gen --help       このヘルプを表示
  sdlc-prompt-gen --version    バージョンを表示

公開ツール:
  generate_prompt        フェーズのプロンプトを生成
  save_artifact          成果物を Vault に保存
  retrieve_wiki_context  過去ドキュメントを検索
  detect_phase           自由文からフェーズを推定

環境変数:
  VAULT_PATH             成果物の保存ルート（未設定なら ./vault）
"""


def main(argv: list[str] | None = None) -> int:
    """CLI エントリポイント。引数を捌いてから MCP サーバーを起動する。"""
    args = sys.argv[1:] if argv is None else argv

    if any(a in ("-h", "--help") for a in args):
        print(_USAGE)
        return 0
    if any(a in ("-V", "--version") for a in args):
        print(f"sdlc-prompt-gen {__version__}")
        return 0
    if args:
        sys.stderr.write(f"不明な引数です: {' '.join(args)}\n\n{_USAGE}")
        return 2

    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
