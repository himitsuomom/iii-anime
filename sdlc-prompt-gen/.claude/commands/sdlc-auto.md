---
description: SDLC フェーズを自動判定して該当フェーズを実行
argument-hint: [やりたいこと or コンテキスト]
allowed-tools:
  - mcp__sdlc-prompt-gen__detect_phase
  - mcp__sdlc-prompt-gen__generate_prompt
  - mcp__sdlc-prompt-gen__save_artifact
  - mcp__sdlc-prompt-gen__retrieve_wiki_context
  - Read
  - Grep
  - Glob
model: claude-sonnet-4-6
---

# SDLC Auto: フェーズ自動判定

## Step 1 — フェーズを推定

`mcp__sdlc-prompt-gen__detect_phase` を呼び、text="$ARGUMENTS" で
phase と confidence を取得する。

- confidence が低い（< 0.6）か phase=0 のときは、推定結果をユーザーに提示し、
  どのフェーズで進めるか確認してから次へ進む。
- confidence が十分なら、その phase で続行する。

## Step 2 — 過去の知見を参照

`mcp__sdlc-prompt-gen__retrieve_wiki_context` を呼び、
query="$ARGUMENTS と類似する過去案件" で関連ドキュメントを最大5件取得する。

## Step 3 — プロンプト生成（必須）

判定した phase で **必ず** `mcp__sdlc-prompt-gen__generate_prompt` を呼ぶこと:
- phase: 推定された番号
- project_context: "$ARGUMENTS"
- response_format: "detailed"

## Step 4 — 成果物を生成して Vault に保存

生成プロンプトに従って成果物を作成し、`mcp__sdlc-prompt-gen__save_artifact` で
Vault に保存する（phase / title / content / project）。

## Step 5 — サマリ

判定フェーズ・確信度・作成したファイル一覧を提示する。
別フェーズで続けるなら対応する `/sdlc-phase-N` を案内する。
