# sandbox と build ループ — 実装レベル詳細

> 親: [`P0-DETAIL.md`](./P0-DETAIL.md) / 採用案: 案A（iii-exec 自前実行）
> 案Aで最も load-bearing な 2 ピースを実装直前まで確定する:
> **(1) sandbox の実体**（コマンド実行/ファイル編集の手足）と
> **(2) build の Claude tool-use ループ**（頭脳と手足の接続）。

---

## A. 重要な前提（調査で確定した事実）

- `iii-exec`（engine の `shell` ワーカー）は **`register_functions` が空** = **呼び出し可能関数を持たない**。
  起動時に `exec:` のコマンド列を順次実行し、最後のコマンドを常駐させる「**起動時パイプライン専用**」。
- したがって **オンデマンドの `sandbox::exec` は自前で新設する**（既存流用は不可）。
- `iii-exec` の使い道は **「studio ワーカー本体プロセスの起動」**。例:
  ```yaml
  # local.yml
  - name: iii-exec
    config:
      exec:
        - cd app-studio && pnpm install
        - cd app-studio && pnpm build
        - cd app-studio && node dist/index.js   # ← studio ワーカー常駐（registerWorker する）
  ```
  → studio ワーカーが engine に接続し、`sandbox::*` / `studio::*` 関数を `registerFunction` する。

---

## B. sandbox の実体（手足）

studio ワーカー内の Node 関数として実装。Node の `child_process`/`fs` を **隔離 workdir に閉じて**使う。

### B.1 隔離方針（P0 の最小ライン）

| 項目 | 方針 |
|---|---|
| workdir | `/work/<project_id>/`。プロジェクト毎に作成、相互不可視。`sandbox::*` は **この配下のみ** |
| パス検証 | 受領 path を `path.resolve(workdir, p)` → `workdir` の接頭辞一致を必須。`..`/絶対/シンボリックリンク逸脱は拒否 |
| コマンド | **allowlist の実行ファイルのみ**。`&&`/`|`/`;`/バッククォート/`$()` を含む文字列は拒否（1 コマンド=1 実行ファイル） |
| 作業ディレクトリ | 既定 cwd=workdir。`cwd` 引数を取る場合も workdir 内に限定 |
| timeout | 既定 120s/コマンド、上限あり。超過で SIGKILL |
| ネットワーク | P0 は「依存取得(install)時のみ許可」。生成コード実行(test/build)は原則オフライン化を推奨（P1で厳格化） |
| 環境変数 | 最小化。シークレットは渡さない（Vault は deliver の push 時のみ） |

> 強隔離（コンテナ/MicroVM/別ユーザ）は P1。P0 は「allowlist＋workdir 境界＋timeout」を必須最低ラインとする。
> ※ engine 側には rootfs オーバーレイ等の隔離基盤（`iii-worker`）があり、P1 でここへ寄せる選択肢がある。

### B.2 allowlist 初期セット（web-node 前提）

```
node, pnpm, npm, npx, git, ls, cat, mkdir, rm, mv, cp, sed, grep, find, test, echo, true
```
- `rm`/`mv` 等の破壊系も workdir 境界内に閉じる（実体は spawn の cwd と引数 path 検証で担保）。
- 実行ファイル名は `cmd` 文字列の先頭トークンで判定し、未登録なら即拒否。

### B.3 関数シグネチャ（確定）

```ts
// コマンド実行（bash ツールの実体）
iii.registerFunction('sandbox::exec', async (input: {
  project_id: string
  cmd: string                 // 例: "pnpm test"。シェル演算子は禁止
  cwd?: string                // workdir 相対。省略時 workdir 直下
  timeout_ms?: number         // 既定 120000
}): Promise<{
  stdout: string; stderr: string; exit_code: number; timed_out: boolean
}> => { /* allowlist 検証 → spawn(file, args, {cwd, timeout}) → 収集 */ })

// ファイル編集（text editor ツールの実体）。Claude の text_editor コマンドに対応
iii.registerFunction('sandbox::edit', async (input: {
  project_id: string
  command: 'view' | 'create' | 'str_replace' | 'insert'
  path: string                                  // workdir 相対
  file_text?: string                            // create
  old_str?: string; new_str?: string            // str_replace（一意一致のみ）
  insert_line?: number; insert_text?: string    // insert
  view_range?: [number, number]                 // view
}): Promise<{ ok: boolean; content?: string; diff?: string; error?: string }>
 => { /* path 検証 → fs 操作。str_replace は 0/複数一致をエラーに */ })
```

---

## C. build の Claude tool-use ループ（頭脳↔手足）

`studio::build::run` の内部。Anthropic 公式 SDK(`@anthropic-ai/sdk`)で、
**Anthropic 定義のクライアント実行ツール**（`bash_20250124` と `text_editor_20250728`）を宣言し、
Claude の `tool_use` を **sandbox 関数へ橋渡し**する手動ループ。

### C.1 モデル/パラメータ

- model: `claude-opus-4-8`、thinking: `{type:'adaptive'}`、`output_config:{effort:'xhigh'}`（コーディング）。
- 大きめ出力に備え **streaming** + `get_final_message()`（`max_tokens` は 16k〜、stream時は最大限）。
- **prompt caching**: 不変な接頭辞（システムプロンプト＋確定 Spec/Plan）に `cache_control` を置く。
  ツール定義は先頭に描画され不変に保つ（ツール集合を途中で変えない）。
- **`stop_reason==='refusal'`** を必ず分岐（content 参照前にチェック）。
- ガード: `maxTurns`（例 40）と上位の `max_iterations`（QA差し戻し回数）で二重に暴走防止。

### C.2 ツール定義（schema-less、クライアント実行）

```ts
const tools = [
  { type: 'bash_20250124', name: 'bash' },
  { type: 'text_editor_20250728', name: 'str_replace_based_edit_tool' },
]
```
- `bash` 入力: `{command}` または `{restart:true}` → `sandbox::exec` へ。
- text editor 入力: `command∈{view,create,str_replace,insert}` ＋ path 等 → `sandbox::edit` へ。

### C.3 手動ループ（擬似コード）

```ts
async function buildRun({ project_id, feedback }) {
  const st = await iii.state.get<ProjectState>({ key: project_id })
  const system = [
    { type:'text', text: BUILD_SYSTEM_PROMPT },                       // 不変
    { type:'text', text: renderSpecPlan(st.spec, st.plan),
      cache_control:{ type:'ephemeral' } },                            // 案件内で不変 → キャッシュ
  ]
  const messages = [{ role:'user', content: feedback
      ? `前回の不合格を修正せよ。理由:\n${feedback}`
      : `次の仕様/計画でアプリを実装し、テストが緑になるまで仕上げよ。workdir=${st.workdir}` }]

  for (let turn = 0; turn < MAX_TURNS; turn++) {
    const res = await anthropic.messages.stream({
      model:'claude-opus-4-8', max_tokens: 32000,
      thinking:{ type:'adaptive' }, output_config:{ effort:'xhigh' },
      system, tools, messages,
    }).finalMessage()

    if (res.stop_reason === 'refusal') { /* 失敗記録 → throw */ }
    messages.push({ role:'assistant', content: res.content })   // tool_use ブロック保持必須

    const toolUses = res.content.filter(b => b.type === 'tool_use')
    if (toolUses.length === 0) break                            // end_turn = 実装完了

    const results = []
    for (const t of toolUses) {                                 // 並列実行可、結果は1メッセージに集約
      const out = (t.name === 'bash')
        ? await iii.trigger({ function_id:'sandbox::exec',
            payload:{ project_id, cmd: t.input.command } })
        : await iii.trigger({ function_id:'sandbox::edit',
            payload:{ project_id, ...mapEditorInput(t.input) } })
      results.push({ type:'tool_result', tool_use_id: t.id,
        content: renderToolResult(out), is_error: isError(out) })
    }
    messages.push({ role:'user', content: results })            // 全 tool_result を1メッセージで返す
  }

  const files = await listWorkdir(project_id)
  await iii.state.update({ key: project_id,
    data:{ status:'qa', artifacts:{ files } } })
  // → orchestrator へ build.done 通知（§3）
}
```

要点:
- `assistant` の `content`（tool_use 含む）を**丸ごと** messages に積む。
- 同一ターンの **tool_result は 1 つの user メッセージにまとめる**（分割すると並列ツール抑制を学習する）。
- ツール結果は文字列化（exec は `exit_code/stdout/stderr` を要約、edit は `diff`）。失敗は `is_error:true`。
- `sandbox::*` は **iii 関数**経由なので、実行が**そのまま iii のトレースに乗る**（可観測性が自動で付く）。

---

## D. P0 確定型（Spec / Plan / Rubric / QaResult / Artifacts）

```ts
type Spec = {
  goal: string                       // 一文要約
  features: string[]                 // 必須機能（受け入れ条件の素）
  acceptance: string[]               // 「これが満たされたら完成」= QA ルーブリックの素
  constraints?: string[]             // 技術/非機能の制約
  assumptions: string[]              // intake が補った仮定（P0は質問せず明示）
}

type Plan = {
  app_type: 'web-node'               // P0 は固定。P1 でアダプタ選択
  stack: string[]                    // 例: ["node","react","vite","vitest"]
  tasks: string[]                    // 実装手順の分解
  build_cmd: string                  // "pnpm build"
  test_cmd: string                   // "pnpm test"
  run_cmd?: string                   // "pnpm preview"
}

type Rubric = {                       // successCheck 由来。QA が機械判定 + 加点
  hard: Array<{ id:string; cmd:string; expect:'exit0' }>   // 必須（test/build 緑）
  soft?: Array<{ id:string; check:string }>                // 仕様適合(Claude レビュー)
}

type QaResult = {
  passed: boolean
  failures: string[]                 // 失敗基準と要点（build への feedback になる）
  score: number                      // 0-100（soft 加点込み）
  logs_ref?: string
}

type Artifacts = {
  files: string[]                    // workdir 相対パス一覧
  repo_url?: string                  // P1: git push 先
  preview_url?: string               // P1: runCmd 公開
}
```

QA の合否は **hard 基準（test/build が exit0）を AND**で必須、soft はスコア加点のみ（P0 は hard だけでも可）。

---

## E. これで P0 着手可能になる順序（更新）

1. **sandbox::exec / sandbox::edit**（§B）— 最優先。allowlist＋workdir 境界＋timeout のユニットテストまで。
2. studio ワーカー雛形＋`local.yml`（`iii-exec` で起動）＋state スキーマ＋orchestrator 遷移表。
3. intake(Sonnet で Spec) → design(Opus で Plan)。
4. **build::run**（§C のループ）— 中核。
5. qa::evaluate（Rubric.hard を sandbox::exec 実行で判定）。
6. deliver::package（local artifact）。
7. E2E スモーク（小さな web アイデア → delivered）。

---

## F. 次に詰める候補（さらに深掘りするなら）

- **BUILD_SYSTEM_PROMPT の本文設計**（効率的な tool 使用・workdir 規約・テスト駆動の指示・冗長narration抑制）。
- intake/design の**プロンプト＋ JSON 構造化出力**（`output_config.format` で Spec/Plan を schema 拘束）。
- **idempotency / 再開**（同 project_id 再投入、ターン途中のクラッシュ復帰、workdir のクリーンアップ）。
- **コスト試算**（1案件あたり: build 平均ターン数 × トークン × 単価、QA 反復回数の期待値）。
- **強隔離への移行**（P1: engine の `iii-worker` rootfs オーバーレイ/ MicroVM へ sandbox を寄せる）。
