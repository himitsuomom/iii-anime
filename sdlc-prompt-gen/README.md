# sdlc-prompt-gen

SDLC（ソフトウェア開発ライフサイクル）の **10フェーズ** それぞれに最適化したプロンプトを生成し、成果物をローカルの Vault（Markdown 置き場）に蓄積する **MCP サーバー**です。Claude Code から `/sdlc-phase-1` などのスラッシュコマンドで呼び出して使います。

このプロジェクトは「初心者でも迷わない」ことを目標に、**インストール → 初回起動 → トラブル対処**まで実際のコマンドで書いてあります。上から順にコピペすれば動きます。

---

## これは何をするもの？

- **`generate_prompt`** — フェーズ番号とプロジェクト概要を渡すと、そのフェーズ専用の `system_prompt` / `user_prompt` を返します。
- **`save_artifact`** — 生成した成果物を `VAULT_PATH/prompts/YYYY/MM/{phase}-{slug}.md` に frontmatter 付きで保存します。
- **`retrieve_wiki_context`** — 過去に保存した成果物を検索して、関連ドキュメントを返します（過去の知見の再利用）。
- **`detect_phase`** — 「このAPIのテストを書きたい」のような自由文から、今どのフェーズかを推定します。

10フェーズ:

| # | フェーズ | 適用思想 |
|---|---|---|
| 1 | 構想・企画 | 復唱プロンプト + メタプロンプト |
| 2 | 要件定義 | MoSCoW + 受け入れ基準 |
| 3 | 設計（System/DB/API） | Triangle（Context/Spec/Constraints） |
| 4 | バックエンド実装 | 契約優先 + 小さな差分 |
| 5 | フロントエンド実装 | コンポーネント分割 + 状態の局所化 |
| 6 | バックエンドテスト | SDLC品質ゲート 6観点 |
| 7 | バックエンドデバッグ | 仮説→再現→最小修正 |
| 8 | フロントエンドテスト | ユーザー操作起点の E2E |
| 9 | 結合・リリース | チェックリスト + ロールバック前提 |
| 10 | フロントエンドデバッグ | Phase7同型 + UI観点 |

---

## 必要なもの

- **Python 3.10 以上**
- **[uv](https://docs.astral.sh/uv/)**（パッケージ管理・実行ツール）
- **Claude Code**（このサーバーを使う側）

uv が入っているか確認:

```bash
uv --version
```

入っていなければインストール（macOS / Linux）:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## インストール

```bash
# 1. このディレクトリに入る
cd sdlc-prompt-gen

# 2. 仮想環境を作って依存をインストール（dev 込み）
uv venv
uv pip install -e ".[dev]"
```

> `uv venv` は `.venv/` を作ります。以降のコマンドは `uv run ...` で実行すれば、自動で `.venv` を使うので `activate` は不要です。

---

## 初回起動：まず動作確認

インストール直後に、サーバーが起動できる状態かを **サーバーを立ち上げずに** 確認できます。

```bash
# バージョン表示（即座に終了する）
uv run sdlc-prompt-gen --version
# => sdlc-prompt-gen 0.1.0

# 使い方表示（即座に終了する）
uv run sdlc-prompt-gen --help
```

> **補足:** 引数なしで `uv run sdlc-prompt-gen` を実行すると、MCP サーバーが **stdio で待ち受け状態**に入ります（プロンプトが返ってこないのが正常）。これは Claude Code が内部的に起動するための動作なので、手動で叩く必要はありません。止めるときは `Ctrl-C`。

テストを流して全機能が健全か確認:

```bash
uv run pytest -q
# => 14 passed
```

---

## Claude Code に登録する

### 方法 A: 配布版（uvx）を使う

リポジトリを公開・配布している場合は `.mcp.json` をそのまま使えます。プロジェクトのルートに置いてください。

```jsonc
{
  "mcpServers": {
    "sdlc-prompt-gen": {
      "command": "uvx",
      "args": ["--from", "sdlc-prompt-gen", "sdlc-prompt-gen"],
      "env": { "VAULT_PATH": "${VAULT_PATH}" }
    }
  }
}
```

### 方法 B: ローカルのソースを直接使う（開発中はこちら）

`.mcp.local.json` をコピーして、`--directory` を **このフォルダの絶対パス**に書き換えます。

```bash
cp .mcp.local.json /path/to/your-project/.mcp.json
```

```jsonc
{
  "mcpServers": {
    "sdlc-prompt-gen": {
      "command": "uv",
      "args": ["run", "--directory", "/ABSOLUTE/PATH/TO/sdlc-prompt-gen", "sdlc-prompt-gen"],
      "env": { "VAULT_PATH": "${VAULT_PATH}" }
    }
  }
}
```

絶対パスはこれで取れます:

```bash
pwd   # 例: /Users/you/repos/sdlc-prompt-gen
```

### Vault の場所を指定する

成果物の保存先を環境変数 `VAULT_PATH` で指定します（未設定なら実行ディレクトリ直下の `./vault`）。

```bash
export VAULT_PATH="$HOME/Documents/llm wiki"
```

### スラッシュコマンドを入れる

`.claude/commands/` に `/sdlc-phase-1` … `/sdlc-phase-10` と `/sdlc-auto` を同梱しています。使うプロジェクトにコピーします。

```bash
cp -r .claude/commands /path/to/your-project/.claude/
```

### 反映

Claude Code を **再起動**し、`/mcp` と打って `sdlc-prompt-gen` が `connected` で出ればOKです。

---

## 使ってみる

```text
/sdlc-phase-1 家計簿アプリを作りたい
```

または、フェーズを自動判定させたい場合:

```text
/sdlc-auto このAPIのテストコードとカバレッジを用意したい
```

各コマンドは内部で `retrieve_wiki_context`（過去知見の参照）→ `generate_prompt`（プロンプト生成）→ 成果物作成 → `save_artifact`（Vault 保存）の順に進みます。

保存されるパスの規約:

```
{VAULT_PATH}/prompts/2026/06/3-ecサイト.md
                     └YYYY└MM └phase-slug
```

---

## トラブル対処

| 症状 | 原因 | 対処 |
|---|---|---|
| `/mcp` に `sdlc-prompt-gen` が出ない | `.mcp.json` が読まれていない / パス誤り | プロジェクトルートに `.mcp.json` があるか、`--directory` の絶対パスが正しいか確認し、Claude Code を再起動 |
| `failed to start` / `command not found: uv` | uv 未インストール、または PATH に無い | `uv --version` を確認。無ければ上記の手順でインストールし、シェルを開き直す |
| `--help` が返らず固まる | 古い版で `mcp.run()` が引数を解釈していた | 本リポジトリでは修正済み。`uv pip install -e .` で入れ直す（`--help` は即座に終了します） |
| `Readme file does not exist: README.md` でビルド失敗 | `pyproject.toml` が `README.md` を参照しているのにファイルが無い | このフォルダ直下に `README.md`（本ファイル）がある状態でインストールする |
| 成果物が見つからない | `VAULT_PATH` 未設定で `./vault` に保存されている | `echo $VAULT_PATH` を確認し、必要なら `export VAULT_PATH=...` してから登録し直す |
| `No module named pytest` | dev 依存が未インストール | `uv pip install -e ".[dev]"` を実行 |

サーバーが起動するかだけを切り分けたいときは、Claude Code を介さず単体で確認できます:

```bash
uv run sdlc-prompt-gen --version   # 即 0 で終了すれば実行系はOK
uv run pytest -q                   # ロジックの健全性を確認
```

---

## 開発

```bash
uv run pytest -q          # テスト（14件）
uv run ruff check src     # Lint
```

ディレクトリ構成:

```
sdlc-prompt-gen/
├── README.md
├── pyproject.toml
├── .mcp.json / .mcp.local.json     # Claude Code 登録用
├── src/sdlc_prompt_gen/
│   ├── server.py                   # MCP サーバー + CLI（--help/--version）
│   ├── phases.py                   # 10フェーズ定義（get_phase）
│   ├── detect/phase_detector.py    # detect_phase
│   ├── generators/builder.py       # build_prompt
│   ├── vault/store.py              # save_artifact / retrieve_context
│   └── templates/                  # phase-1.md … phase-10.md
├── .claude/commands/               # /sdlc-phase-1 … 10, /sdlc-auto
└── tests/                          # 14 テスト
```

---

## ライセンス

Apache-2.0
