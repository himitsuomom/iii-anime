---
description: SDLC Phase 8 - フロントエンドテスト
argument-hint: [プロジェクト概要 or コンテキスト]
allowed-tools:
  - mcp__sdlc-prompt-gen__generate_prompt
  - mcp__sdlc-prompt-gen__save_artifact
  - mcp__sdlc-prompt-gen__retrieve_wiki_context
  - Read
  - Grep
  - Glob
model: claude-haiku-4-5
---

# SDLC Phase 8: フロントエンドテスト

適用思想: **ユーザー操作起点の E2E 観点**

## Step 1 — 過去の知見を参照

`mcp__sdlc-prompt-gen__retrieve_wiki_context` を呼び、
query="$ARGUMENTS と類似する過去案件" で関連ドキュメントを最大5件取得する。

## Step 2 — プロンプト生成（必須）

**必ず** `mcp__sdlc-prompt-gen__generate_prompt` を呼ぶこと:
- phase: 8
- project_context: "$ARGUMENTS"
- response_format: "detailed"

返却された system_prompt / user_prompt を使ってこのフェーズの成果物を生成する。
自分でプロンプトを創作せず、必ず MCP ツールに委譲すること。

## Step 3 — 成果物を生成

生成プロンプトに従って成果物を作成し、`frontend/__tests__/` 配下に保存する。

## Step 4 — Vault に蓄積

`mcp__sdlc-prompt-gen__save_artifact` を呼び、生成プロンプトを Vault に保存する:
- phase: 8
- title: 成果物のタイトル
- content: 生成したプロンプトまたは成果物
- project: プロジェクト名

## Step 5 — サマリ

作成したファイル一覧を提示する。次のフェーズ: /sdlc-phase-9
