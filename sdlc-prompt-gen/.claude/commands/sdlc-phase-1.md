---
description: SDLC Phase 1 - 構想・企画
argument-hint: [プロジェクト概要 or コンテキスト]
allowed-tools:
  - mcp__sdlc-prompt-gen__generate_prompt
  - mcp__sdlc-prompt-gen__save_artifact
  - mcp__sdlc-prompt-gen__retrieve_wiki_context
  - Read
  - Grep
  - Glob
model: claude-opus-4-7
---

# SDLC Phase 1: 構想・企画

適用思想: **復唱プロンプト + メタプロンプト**

## Step 1 — 過去の知見を参照

`mcp__sdlc-prompt-gen__retrieve_wiki_context` を呼び、
query="$ARGUMENTS と類似する過去案件" で関連ドキュメントを最大5件取得する。

## Step 2 — プロンプト生成（必須）

**必ず** `mcp__sdlc-prompt-gen__generate_prompt` を呼ぶこと:
- phase: 1
- project_context: "$ARGUMENTS"
- response_format: "detailed"

返却された system_prompt / user_prompt を使ってこのフェーズの成果物を生成する。
自分でプロンプトを創作せず、必ず MCP ツールに委譲すること。

## Step 3 — 成果物を生成

生成プロンプトに従って成果物を作成し、`docs/sdlc/phase-1/` 配下に保存する。

## Step 4 — Vault に蓄積

`mcp__sdlc-prompt-gen__save_artifact` を呼び、生成プロンプトを Vault に保存する:
- phase: 1
- title: 成果物のタイトル
- content: 生成したプロンプトまたは成果物
- project: プロジェクト名

## Step 5 — サマリ

作成したファイル一覧を提示する。次のフェーズ: /sdlc-phase-2
