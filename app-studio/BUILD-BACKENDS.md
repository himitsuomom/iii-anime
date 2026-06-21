# build の「頭脳」 — 差し替え可能なバックエンド

> 親: [`DESIGN.md`](./DESIGN.md) §5/§6, [`SANDBOX-AND-BUILD-LOOP.md`](./SANDBOX-AND-BUILD-LOOP.md)
> 問い: 「**API でしか動かないの？ この Claude Code から動かせる？**」への答えと設計。

---

## 0. 結論（先に）

- **モデル推論は必ずリモート（Anthropic）**で動く。完全ローカルの Claude は無い。
  → 「どこかで Anthropic に繋がる」のは避けられない。
- ただし **生 API キーを自前配線して従量課金で叩く以外の選択肢がある**。
  **この Claude Code（CLI / Agent SDK）を実装エンジンとして使える**。
- `studio::build` の「頭脳」を **`BuildBackend` インターフェースで差し替え可能**にした。
  - **ClaudeCodeBackend（P0 既定・推奨）**: ローカルの `claude -p` を駆動。
    Claude Code 自身の sandbox/ツール/生成→テスト→修正ループを再利用。
    **既存の Claude Code ログイン認証**を使う（別途 `ANTHROPIC_API_KEY` 配線が不要）。
  - **ApiBackend（将来）**: Anthropic Messages API + 自前 tool-use ループ + 自前 sandbox。
    `ANTHROPIC_API_KEY` 必須・トークン従量。完全な制御。

> **この環境で実証済み**: `ANTHROPIC_API_KEY` 未設定のまま `ClaudeCodeBackend` が
> `claude -p` を起動し、workdir に成果物を生成（e2e テスト緑）。詳細は §4。

---

## 1. `BuildBackend` インターフェース

```ts
interface BuildBackend {
  readonly id: string
  run(req: {
    project_id: string
    workdir: string          // この配下のみで作業
    systemPrompt: string     // BUILD_SYSTEM_PROMPT（append）
    userPrompt: string       // Spec + Plan + 「テストを緑にせよ」
    maxTurns?: number
  }): Promise<{
    ok: boolean              // バックエンド処理が成功（テスト緑かは QA が判定）
    summary: string
    num_turns?: number; cost_usd?: number; session_id?: string
    error?: string; raw?: unknown
  }>
}
```

`studio::build::run` はこの `run()` を呼ぶだけ。バックエンド選択は環境変数
`STUDIO_BUILD_BACKEND=claude-code|api`（既定 `claude-code`）。

---

## 2. ClaudeCodeBackend（推奨）

`claude -p <userPrompt> --append-system-prompt <systemPrompt> --output-format json
 --max-turns N --allowedTools Bash Edit Write Read Glob Grep --permission-mode acceptEdits`
を **cwd=workdir** で spawn し、JSON 結果（`result`/`session_id`/`total_cost_usd`/`num_turns`）をパース。

利点:
- **API キー配線不要**。`claude -p` は**この環境の Claude Code ログイン**をそのまま使う。
- **実装が薄い**: 生成→テスト→修正ループ・bash/edit ツール・サンドボックスは Claude Code 側が持つ。
- **サブスク（Pro/Max）で従量 API 課金なし**に駆動可能（§3 認証）。

無人運転の要点:
- `--allowedTools` で Bash/Edit/Write/Read を事前許可（print モードは未許可ツールを自動拒否＝ハングしない）。
- `--permission-mode acceptEdits`（編集自動承認）。さらに緩めるなら `--dangerously-skip-permissions`
  （**隔離コンテナ/サンドボックス内に限り**）。本実装は `permission: 'acceptEdits' | 'skip'` で選択。
- `--max-turns` と上位 `max_iterations` で二重に暴走防止。

> **隔離モデルの違い**: ClaudeCodeBackend は Claude Code 自身のサンドボックス＋ephemeral コンテナ＋
> cwd スコープ＋allowedTools を境界とする（自前 `sandbox::exec` allowlist は通らない）。
> 一方 ApiBackend は自前 `sandbox::exec/edit`（allowlist＋workdir 封じ込め）が境界。
> どちらでも **QA の testCmd 実行**は自前 sandbox を使えるので、sandbox 実装は無駄にならない。

---

## 3. 認証マトリクス

| 駆動方法 | 必要な認証 | 従量 API 課金 |
|---|---|---|
| `claude -p`（CLI ヘッドレス） | **既存の Claude Code ログイン**で可（`~/.claude` 認証） | サブスクなら**なし** |
| Claude Agent SDK（`@anthropic-ai/claude-agent-sdk`） | `CLAUDE_CODE_OAUTH_TOKEN`（`claude setup-token` で発行）または `ANTHROPIC_API_KEY` | トークン=サブスク / API キー=従量 |
| ApiBackend（Anthropic SDK 直） | `ANTHROPIC_API_KEY` | **あり**（[COST-MODEL.md](./COST-MODEL.md)） |
| クラウド経由 | `CLAUDE_CODE_USE_BEDROCK/VERTEX` 等 | 各プラットフォーム課金 |

- **サブスク運用**: `claude setup-token`（要ブラウザ初回ログイン, 1年有効）→ `CLAUDE_CODE_OAUTH_TOKEN` を
  worker ホストに設定。これで SDK でも従量 API 課金なし。
- 注意: `ANTHROPIC_API_KEY` が設定されているとサブスク認証より優先される。

---

## 4. この環境での実証（再現手順）

```bash
cd app-studio
STUDIO_E2E=1 pnpm exec tsx --test src/build/claude-code-backend.test.ts
```

- 前提: `claude` CLI がログイン済み（本環境は `ANTHROPIC_API_KEY` **未設定**）。
- 結果: ClaudeCodeBackend が `claude -p` を起動 → 一時 workdir に `BUILT.txt`(=`DONE`) を生成 →
  アサート緑（約12秒）。**API キーなしで実ビルドが成立**することを確認。
- 通常の `pnpm test` では e2e はスキップ（トークン消費を避けるため `STUDIO_E2E=1` でのみ実行）。

---

## 5. P0 での既定と移行

- **P0 既定 = ClaudeCodeBackend**（最短・API キー不要・この Claude Code から動く）。
- ApiBackend は自前 sandbox（実装済み）＋ tool-use ループ（[設計](./SANDBOX-AND-BUILD-LOOP.md) §C）で後日実装。
  細粒度制御・コスト最適化（増分キャッシュ）・厳格 allowlist が要る工程で選択。
- 切替は `STUDIO_BUILD_BACKEND` のみ。orchestrator/qa/deliver は backend 非依存。

---

## 6. 正直な但し書き

- 「**API でしか動かない**」わけではない＝**生 API キー配線と従量課金が必須ではない**、という意味。
  モデル推論自体は常にリモート（Anthropic）で行われる（ローカル LLM ではない）。
- サブスクのレート/利用上限の範囲で動く。大量・並列の無人運転はプランの上限に従う。
