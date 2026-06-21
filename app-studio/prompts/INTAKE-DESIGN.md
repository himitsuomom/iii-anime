# intake / design — プロンプト ＋ 構造化出力設計

> 親: [`../P0-DETAIL.md`](../P0-DETAIL.md) §1, [`../SANDBOX-AND-BUILD-LOOP.md`](../SANDBOX-AND-BUILD-LOOP.md) §D
> 目的: `intake::spec` と `design::plan` の出力を **`output_config.format`(JSON schema) で拘束**し、
> パースエラー・欠損フィールドをゼロにする。

---

## 0. 構造化出力の前提（制約に合わせる）

`messages.parse()` + `output_config:{format:{type:'json_schema', schema}}` を使う。
**サポートされる JSON schema 機能に限定**して設計する:

- 使える: 基本型 / `enum` / `const` / `anyOf` / `$ref` / 文字列フォーマット / `additionalProperties:false`(必須) / `required`。
- **使えない**: 再帰、数値制約(`minimum`/`maximum`)、文字列長(`minLength`/`maxLength`)、複雑な配列制約。
  → 「3個以上」等は schema で縛らず**プロンプトで指示**する。
- 新スキーマ初回はコンパイルで一度だけレイテンシ増（以後 24h キャッシュ）。
- 対応モデル: **Sonnet 4.6 / Opus 4.8** とも対応（intake=Sonnet, design=Opus で問題なし）。
- `citations` や assistant prefill とは併用不可（本用途では使わない）。

> Python/TS SDK は未対応制約を自動で除去＋クライアント検証するが、**最初から非対応制約を書かない**方針。

---

## 1. Spec スキーマ（`intake::spec` の出力）

```ts
// zodOutputFormat(SpecSchema) を output_config.format に渡す
const SpecSchema = z.object({
  goal: z.string().describe('One-sentence summary of what the app should do'),
  features: z.array(z.string()).describe('Required features, user-visible'),
  acceptance: z.array(z.string())
    .describe('Concrete, checkable "done" conditions — basis of the QA rubric'),
  constraints: z.array(z.string()).describe('Tech/non-functional constraints'),
  assumptions: z.array(z.string())
    .describe('Gaps you filled in because the idea was underspecified'),
}).strict()   // → additionalProperties:false
```

> P0 は「**質問せず仮定で前進**」。曖昧さは `assumptions` に必ず明示させる（後で人が見て修正できる）。

### intake プロンプト（モデル: `claude-sonnet-4-6`）

```text
[system]
You turn a rough product idea into a precise, buildable specification for a
small web application. You do not ask questions — if the idea is underspecified,
choose sensible, minimal defaults and record each choice in "assumptions".

Rules:
- "acceptance" must be concrete and machine-checkable wherever possible
  (e.g. "GET /todos returns 200 with a JSON array", not "the API works well").
- Keep scope minimal: only what the idea implies. No speculative features.
- Provide at least 3 acceptance items and list every non-obvious choice in
  "assumptions".

[user]
Idea:
<idea>

Produce the specification.
```

- `effort`: `medium`（対話的・軽量）。`max_tokens` 4k 程度。
- 出力は `SpecSchema` に拘束 → そのまま `state.spec` へ保存。

---

## 2. Plan スキーマ（`design::plan` の出力）

```ts
const PlanSchema = z.object({
  app_type: z.enum(['web-node']),                  // P0 固定。P1 でアダプタ拡張
  stack: z.array(z.string()).describe('e.g. ["node","react","vite","vitest"]'),
  tasks: z.array(z.string()).describe('Ordered implementation steps'),
  build_cmd: z.string(),                            // "pnpm build"
  test_cmd: z.string(),                             // "pnpm test"
  run_cmd: z.string().optional(),                   // "pnpm preview"
}).strict()
```

### design プロンプト（モデル: `claude-opus-4-8`）

```text
[system]
You are a software architect. Given a specification, produce a concrete,
minimal implementation plan for a single-package web application (app_type
"web-node"). Choose a small, well-supported stack. The plan must be directly
executable by an autonomous coding agent.

Rules:
- "tasks" is an ordered, dependency-respecting list of implementation steps.
- "test_cmd" and "build_cmd" must be runnable as single commands and must be the
  exact commands the QA step will run to decide pass/fail.
- Prefer the simplest stack that satisfies the spec. Do not over-engineer.

[user]
Specification:
<spec JSON>

Produce the plan.
```

- `effort`: `high`。`max_tokens` 4k。出力は `PlanSchema` 拘束 → `state.plan` へ。
- `app_type` を `enum(['web-node'])` に固定することで、P0 の対象外種別への逸脱を schema で禁止。

---

## 3. 呼び出し形（TS, `messages.parse`）

```ts
import { zodOutputFormat } from '@anthropic-ai/sdk/helpers/zod'

const res = await anthropic.messages.parse({
  model: 'claude-sonnet-4-6', max_tokens: 4000,
  output_config: { format: zodOutputFormat(SpecSchema), effort: 'medium' },
  system: INTAKE_SYSTEM,
  messages: [{ role:'user', content: `Idea:\n${idea}\n\nProduce the specification.` }],
})
const spec = res.parsed_output           // null ならパース失敗 → リトライ/フォールバック
```

- `parsed_output` が null（拘束失敗 or `stop_reason:'max_tokens'`）の場合は max_tokens 増やして 1 回リトライ、
  なお失敗なら `error` イベントで失敗扱い。
- `stop_reason:'refusal'` を分岐（content 参照前）。

---

## 4. acceptance → Rubric への橋渡し

- `Spec.acceptance[]` と `Plan.test_cmd/build_cmd` から QA の `Rubric` を機械生成:
  - `hard`: `[{id:'build', cmd: build_cmd, expect:'exit0'}, {id:'test', cmd: test_cmd, expect:'exit0'}]`
  - `soft`: 各 `acceptance` 項目を Claude(Opus) によるレビュー観点に（P0 は任意・加点のみ）。
- これにより「**受け入れ条件＝採点基準**」が一気通貫で繋がり、build の done 定義と QA が一致する。
