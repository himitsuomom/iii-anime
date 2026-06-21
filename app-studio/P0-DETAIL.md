# P0 詳細設計 — iii-exec 自前実行モデル

> 親設計: [`DESIGN.md`](./DESIGN.md) / 採用案: **案A（iii-exec で自前実行）**
> 目的: アイデア → 生成 → 自動テスト → 修正 → 納品 が **web 1 種別**で端から端まで通る MVP 骨格。
> 本書は iii-sdk(Node) の実 API（`registerWorker` / `registerFunction` / `registerTrigger` /
> `trigger(...TriggerAction)` / `iii.state.*`）に準拠して関数・イベント・状態遷移を確定する。

---

## 0. 実行モデル（案A の具体）

```
studio::build (実装ワーカー)
  └─ Claude API (messages + tool use: bash / str_replace_based_edit_tool)
        │  Claude が「このコマンドを実行/このファイルを編集」を tool_use で要求
        ▼
  └─ sandbox::exec / sandbox::edit  ← iii 関数。隔離 workdir 内で実体実行（iii-exec/shell 基盤）
        │  stdout/exit_code/diff を tool_result として Claude へ返す
        ▼
  └─ ループ（end_turn まで）→ 生成物が workdir に揃う
```

- **頭脳**: Claude（役割別モデルは DESIGN §6）。実装は `claude-opus-4-8`、effort=`xhigh`。
- **手足**: `sandbox::exec`（コマンド実行）/ `sandbox::edit`（ファイル編集）を iii 関数として実装し、
  **プロジェクト専用の隔離 workdir**（`/work/<project_id>/`）でのみ動かす。
- **QA ループの所有者**: `studio::orchestrator`。`studio::qa` の合否イベントで build へ差し戻す
  （Managed Agents の Outcome は使わない=案A）。

> セキュリティ: `sandbox::exec` は許可コマンドの allowlist＋workdir 外アクセス禁止＋タイムアウト＋
> ネットワーク制限を必須とする（生成コードは信頼しない）。

---

## 1. ワーカー / 関数シグネチャ（Node SDK 準拠）

すべて `const iii = registerWorker(process.env.III_URL ?? 'ws://localhost:49134')` 配下。
関数 ID は `studio::<dept>::<action>`。型は TypeScript 表記（実装時に zod 等で検証）。

### 1.1 `studio::intake`（PM / 要件定義）
```ts
// HTTP 入口。アイデアを受けてプロジェクトを起票し、パイプラインを開始
iii.registerFunction('studio::intake::create', async (input: {
  body: { idea: string }
}): Promise<{ status_code: number; body: { project_id: string } }> => { /* ... */ })

// アイデア → 構造化スペック（不足は assumptions に明示。P0 は質問せず仮定で前進）
iii.registerFunction('studio::intake::spec', async (input: {
  project_id: string
}): Promise<{ spec: Spec }> => { /* Claude(Sonnet 4.6) */ })

iii.registerTrigger({ type: 'http', function_id: 'studio::intake::create',
  config: { api_path: '/projects', http_method: 'POST' } })
```

### 1.2 `studio::design`（設計）
```ts
iii.registerFunction('studio::design::plan', async (input: {
  project_id: string
}): Promise<{ plan: Plan }> => { /* Claude(Opus 4.8): app_type 選定 + tasks 分解 */ })
```

### 1.3 `studio::build`（実装 = Claude tool-use ループ）
```ts
iii.registerFunction('studio::build::run', async (input: {
  project_id: string
  feedback?: string        // QA からの差し戻し理由（再実装時）
}): Promise<{ build: BuildResult }> => {
  // 1) state から spec/plan/workdir を取得
  // 2) Claude messages ループ（tools: bash, str_replace_based_edit_tool）
  //    - tool_use(bash)      → sandbox::exec を呼び結果を tool_result で返す
  //    - tool_use(edit)      → sandbox::edit を呼び diff を返す
  //    - stop_reason==end_turn で終了
  // 3) artifacts(ファイル一覧/workdir) を state に記録
})
```

### 1.4 `studio::qa`（独立検証・採点）
```ts
iii.registerFunction('studio::qa::evaluate', async (input: {
  project_id: string
}): Promise<{ result: QaResult }> => {
  // アダプタの testCmd/buildCmd を sandbox::exec で実行 → 緑/赤 を機械判定
  // 任意で Claude(Opus 4.8) による仕様適合レビューを加点
  // → { passed: boolean, failures: string[], score: number }
})
```

### 1.5 `studio::deliver`（納品）
```ts
iii.registerFunction('studio::deliver::package', async (input: {
  project_id: string
}): Promise<{ artifacts: Artifacts }> => {
  // workdir を git init/commit→push（トークンは Vault 由来）or アーカイブ化
  // 任意で runCmd によるプレビュー起動 → preview_url
})
```

### 1.6 `studio::orchestrator`（状態機械）
```ts
// 各工程の完了/失敗を受けて次を起動。P0 は fire-and-forget で連結
iii.registerFunction('studio::orch::advance', async (input: {
  project_id: string
  event: PipelineEvent      // §3 参照
}): Promise<void> => { /* §2 の遷移表に従い次関数を trigger */ })
```

### 1.7 sandbox（手足。案A の中核）
```ts
iii.registerFunction('sandbox::exec', async (input: {
  project_id: string; cmd: string; timeout_ms?: number
}): Promise<{ stdout: string; stderr: string; exit_code: number }> => { /* allowlist + workdir 隔離 */ })

iii.registerFunction('sandbox::edit', async (input: {
  project_id: string; path: string; new_text?: string;
  old_str?: string; new_str?: string   // str_replace 形式
}): Promise<{ ok: boolean; diff: string }> => { /* workdir 内のみ */ })
```

---

## 2. 状態機械（遷移表）

`state.status` を単一の真実とし、orchestrator が遷移を駆動する。

| 現状態 | イベント | ガード | 次状態 | 起動関数 |
|---|---|---|---|---|
| (なし) | `project.created` | — | `intake` | `studio::intake::spec` |
| `intake` | `spec.ready` | spec 妥当 | `design` | `studio::design::plan` |
| `design` | `plan.ready` | app_type 決定済 | `building` | `studio::build::run` |
| `building` | `build.done` | — | `qa` | `studio::qa::evaluate` |
| `qa` | `qa.passed` | passed==true | `delivering` | `studio::deliver::package` |
| `qa` | `qa.failed` | iteration < max | `revising` | `studio::build::run`(feedback付) |
| `qa` | `qa.failed` | iteration ≥ max | `failed` | 通知 |
| `revising` | `build.done` | iteration++ | `qa` | `studio::qa::evaluate` |
| `delivering` | `delivered` | — | `delivered` | 完了通知(preview_url) |
| 任意 | `error` | — | `failed` | 通知 + トレース保全 |

ループ不変条件: `iteration` は build 開始毎に +1、`qa.failed` で `< max_iterations` の時のみ build へ戻る。

---

## 3. イベント／連結方式

P0 は**直接連結**（orchestrator が次関数を fire-and-forget で起動）を採用し、
**観測用にイベントも publish**する（疎結合・将来の差し込み余地）。

```ts
// 直接連結（待たない）
iii.trigger({ function_id: 'studio::design::plan',
  payload: { project_id }, action: TriggerAction.Void() })

// 重い build はキュー経由（並列度/リトライを iii に委譲）
iii.trigger({ function_id: 'studio::build::run',
  payload: { project_id }, action: TriggerAction.Enqueue({ queue: 'studio-build' }) })
```

イベント名（pubsub）: `project.created` / `spec.ready` / `plan.ready` / `build.done` /
`qa.passed` / `qa.failed` / `delivered` / `error`。各イベントは `{ project_id, trace_id, ... }`。

> 各関数は「自分の仕事 → state 更新 → 完了イベント publish ＋ orchestrator へ通知」で終える。
> orchestrator に遷移ロジックを集約することで、工程追加（security-review 等）が表 1 行の追記で済む。

---

## 4. State スキーマ（P0 確定版）

`iii.state.set({ key: project_id, data: {...} })` / `get` / `update`。

```ts
type ProjectState = {
  project_id: string
  idea: string
  status: 'intake'|'design'|'building'|'qa'|'revising'|'delivering'|'delivered'|'failed'
  iteration: number
  max_iterations: number          // 既定 5
  workdir: string                 // /work/<project_id>
  spec?: Spec
  plan?: Plan                     // { app_type: 'web-node', tasks: string[] }
  last_qa?: QaResult              // { passed, failures, score }
  artifacts?: Artifacts           // { repo_url?, preview_url?, files: string[] }
  trace_id?: string
  updated_at: string
}
```

---

## 5. P0 ハッピーパス（シーケンス）

```
POST /projects {idea}
  → intake::create  : state起票(status=intake), workdir作成 → orch.advance(project.created)
  → intake::spec    : Claude(Sonnet) でSpec確定 → status=design → plan
  → design::plan    : Claude(Opus) でapp_type=web-node + tasks → status=building → build(enqueue)
  → build::run      : Claude(Opus,xhigh) tool-useループ→ sandbox::exec/edit でコード生成
                      → status=qa → qa.evaluate
  → qa::evaluate    : sandbox::exec で testCmd/buildCmd → passed?
        ├ passed   → status=delivering → deliver.package
        └ failed   → iteration<max なら status=revising → build::run(feedback)
  → deliver::package: commit/preview → status=delivered, preview_url 返却
```

---

## 6. P0 スコープ境界（やること / やらないこと）

**やる**: 単一 app_type(`web-node`)、build↔qa ループ、state 駆動、HTTP 入口、iii トレース、
最小 sandbox(allowlist/隔離/timeout)、ローカル artifact 出力。

**やらない（P1+）**: 複数 app_type アダプタ、プレビュー常時公開、人間承認ゲート、並列サブエージェント、
Vault 本格運用、コスト統制(Task Budget)、自己拡張(動的 worker add)。

---

## 7. 実装着手順（P0 の作業分解）

1. リポ配置: `app-studio/`（独立 pnpm パッケージ、`iii-sdk` 依存）。`local.yml` でワーカー起動設定。
2. `sandbox::exec` / `sandbox::edit`（隔離 workdir・allowlist・timeout）→ 最優先。ここが案Aの土台。
3. `studio::orchestrator`（state スキーマ＋遷移表＋イベント配線）。
4. `studio::intake`（HTTP 入口 + Claude Sonnet で Spec）。
5. `studio::build`（Claude tool-use ループ ↔ sandbox）。← 中核。
6. `studio::qa`（testCmd 実行 + 合否判定）。
7. `studio::deliver`（local artifact 出力、preview は任意）。
8. E2E: `POST /projects` に小さな web アイデアを投げ、delivered まで通すスモークテスト。

---

## 8. 残課題（P0 着手前に潰す）

- ~~`sandbox::exec` の実体~~ → **決着: 自前関数として新設（[詳細](./SANDBOX-AND-BUILD-LOOP.md)）。**
  `iii-exec`(shell ワーカー) は `register_functions` が空で、起動時パイプライン専用のため呼び出し関数を持たない。
  `iii-exec` は「studio ワーカー本体の起動」にのみ使う（オンデマンド実行には使えない）。
- allowlist の初期セット（`pnpm`,`node`,`git`,`ls`,`cat` … 生成コード実行は workdir 限定）→ [詳細](./SANDBOX-AND-BUILD-LOOP.md)。
- Claude tool 定義: `bash_20250124` + `text_editor_20250728`（schema-less, client実行）を sandbox 関数へ橋渡し → [詳細](./SANDBOX-AND-BUILD-LOOP.md)。
- 失敗時のトレース/再開（idempotency: 同 project_id の再投入で重複生成しない）。
