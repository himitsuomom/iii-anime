# 冪等性 / 再開 設計

> 親: [`P0-DETAIL.md`](./P0-DETAIL.md) §2(状態機械), §4(State)
> 前提: iii のトリガー配送は **at-least-once（重複あり得る）**、コンテナは **ephemeral（クラッシュ/再起動あり）**。
> 目標: **同じ案件を二重生成しない**・**途中失敗から安全に再開できる**。

---

## 0. 原則

1. **State が唯一の真実**。`status` から「次に何をすべきか」を**毎回再導出**する（イベントは補助）。
2. **全関数は再実行安全（idempotent）**。同じ入力で 2 回呼ばれても壊れない/重複しない。
3. **遷移は楽観ロック**で直列化（二重 advance を防ぐ）。
4. **workdir は決定的**（`/work/<project_id>`）。再実行時は方針に従いクリーンに戻す。

---

## 1. 冪等キー

- **`project_id` が冪等キー**。`intake::create` は冪等トークンを受け、既存なら**新規作成せず既存を返す**。
  ```ts
  iii.registerFunction('studio::intake::create', async ({ body }) => {
    const key = body.idempotency_key ?? hash(body.idea)   // クライアント指定優先
    const existing = await iii.state.get({ key: `idem:${key}` })
    if (existing) return { status_code: 200, body: { project_id: existing.project_id } }
    const project_id = `prj_${ulid()}`
    await iii.state.set({ key: `idem:${key}`, data: { project_id } })
    await iii.state.set({ key: project_id, data: initialState(project_id, body.idea) })
    return { status_code: 201, body: { project_id } }
  })
  ```
- HTTP 入口は **冪等トークン**（同一アイデアの二重 POST を吸収）を受け付ける。

---

## 2. 各工程のガード（status による多重実行防止）

各関数は冒頭で「**自分の担当ステータスか**」を確認し、**完了済みなら no-op**:

```ts
// 例: design::plan
const st = await iii.state.get<ProjectState>({ key: project_id })
if (st.status !== 'design') return        // 既に通過済み or 別工程 → 何もしない（再配送吸収）
if (st.plan)                return advance(project_id, 'plan.ready')  // 結果あり→前進だけ
```

→ トリガーが重複配送しても、二重に Plan を作らない。**「結果がある＝やり直さない」**を徹底。

---

## 3. 遷移の楽観ロック（二重 advance 防止）

`orchestrator` の状態遷移は **compare-and-set** で直列化。iii state の `update`（条件付き）か version を使う:

```ts
// status を expected→next に CAS。失敗（誰かが先に遷移）なら諦める
async function transition(project_id, expected, next, patch) {
  const r = await iii.state.update({
    key: project_id,
    // 擬似: where status==expected
    data: { ...patch, status: next, _expect_status: expected },
  })
  return r !== null   // false なら競合 → 後勝ちを捨てる
}
```

> iii の `state.update` の条件付き更新／version 機構の正確な API は実装時に確認（§残課題）。
> 無ければ `iteration` 等を版番号代わりに使う。

---

## 4. クラッシュ再開（工程別）

| 工程 | 途中失敗時の方針 | 再開コスト |
|---|---|---|
| intake / design | **やり直し**（短く安価・純関数的）。出力があればスキップ | 低 |
| **build** | **既定: workdir をクリーンにして再実行**（決定的・確実）。長いので下記の任意チェックポイントあり | 中〜高 |
| qa | **やり直し**（sandbox::exec を再実行するだけ・冪等） | 低 |
| deliver | **やり直し**。push は冪等化（同一コミット/タグの再 push は no-op、ブランチ固定） | 低 |

### build のチェックポイント（任意・コスト削減オプション）
- 各ターン後に `messages`（会話履歴）と workdir スナップショット参照を state/ストアへ保存。
- 再開時はそこから `messages` を復元してループ継続 → **やり直しのトークン浪費を回避**。
- P0 は「クリーン再実行」で十分。チェックポイントは P1 のコスト最適化として導入。

### workdir のクリーン化
```ts
// build 再試行（差し戻し含む）前に、決定的状態へ戻す
async function resetWorkdir(project_id, mode: 'clean' | 'keep') {
  if (mode === 'clean') { await sandboxRm(project_id, '.'); await mkdirWorkdir(project_id) }
  // 'keep'（差し戻しで前回成果物を残して直す場合）は QA feedback 経路で使用
}
```
- **QA 差し戻し**は `keep`（前回コードを直す）、**クラッシュ再実行**は `clean`（汚染回避）が既定。

---

## 5. orchestrator 再起動時のスイープ（イベント取りこぼし対策）

webhook/イベントは取りこぼし得るため、**state を真実として定期スキャン**:

```ts
// 起動時 + cron(例 1分)で、終端でない案件を拾って前進させる
async function sweep() {
  const inflight = await iii.state.list({ /* status ∉ {delivered, failed} */ })
  for (const st of inflight) {
    if (isStuck(st)) await advanceFromStatus(st)   // status から次工程を再導出して起動
  }
}
```

- これにより「イベントは来なかったが state は building のまま」のような**宙吊り案件を自動回収**。
- `isStuck`: `updated_at` が一定時間更新されていない案件（ハング/取りこぼし）を対象に。

---

## 6. 失敗の扱い

- リトライ可能（一時的: ネットワーク/429/5xx）: 指数バックオフで自動再試行（iii のキュー/SDK 再試行を利用）。
- リトライ不可（恒久: refusal / max_iterations 超過 / 仕様破綻）: `status='failed'`＋理由を `history` に記録、通知。
- **部分的副作用の打ち消し**: deliver 前に失敗した場合、外部副作用（push 等）は未発生のため安全。
  push 後の失敗は「同一ブランチへの再 push は冪等」で吸収。

---

## 7. 残課題（実装時に確認）

- iii `state.update` の**条件付き更新 / version（楽観ロック）**の正確な API。無ければ代替（CAS 相当）を実装。
- トリガー**重複配送の実際の頻度**と、`Enqueue` の at-least-once/可視性タイムアウト挙動。
- build チェックポイントの保存先（state は小さく保ちたい → 会話履歴は別ストア/ファイル参照）。
- `sweep` の周期と `isStuck` 閾値（ハング検出 vs 正常な長時間 build の区別）。
