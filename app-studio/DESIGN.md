# 仮想アプリ制作会社 on iii — 設計書 v0.1

> アイデアを入れると、社内の各担当（PM → 設計 → 実装 → QA → 納品）が順に動き、
> **動作検証済みのアプリ**を出力する「仮想アプリ制作会社」を iii の上に構築する。
> 本書は実装前の設計・計画フェーズの成果物。

- 対象アプリ種別: **全種類対応**（Web / API・バックエンド / CLI …）を、差し替え可能なアダプタで実現
- AI エンジン: **未定 → 本書で推奨を提示**（結論: Claude を役割別に使い分け）
- ステータス: ドラフト（合意後に MVP 実装へ）

---

## 1. コンセプト

iii の 3 プリミティブ（**Worker = 社員 / Trigger = 次工程への合図 / Function = 各社員の仕事**）に、
制作会社の各部門をそのまま割り当てる。各社員の「頭脳」は LLM（Claude）。
全工程は iii が自動でトレースするので、**進捗・ボトルネック・失敗箇所が常に可視化**される。

```
[アイデア投入] ──HTTP──▶ studio::intake (PM)
                              │ spec.ready
                              ▼
                         studio::design (設計)
                              │ plan.ready
                              ▼
            ┌──────────▶ studio::build (実装) ──┐
            │                                   │ build.done
   qa.failed │                                   ▼
            └────────── studio::qa (QA) ◀── 動作検証・採点
                              │ qa.passed
                              ▼
                         studio::deliver (納品) ──▶ 成果物 / リポジトリ / プレビューURL
```

---

## 2. iii プリミティブへの割り当て

### 2.1 Workers（部門 = 社員）

| Worker | 役割 | 主な Function | 既定モデル(後述) |
|---|---|---|---|
| `studio::intake` | 要件定義(PM)。アイデアを構造化スペックに。曖昧なら質問を返す | `intake::clarify`, `intake::spec` | Sonnet 4.6 |
| `studio::design` | アーキテクチャ/技術選定/アプリ種別の決定、作業分解 | `design::plan`, `design::pick-apptype` | Opus 4.8 |
| `studio::build` | コード生成＋自己テスト（中核）。アダプタ経由で各種別に対応 | `build::run` | Opus 4.8 (xhigh) / Fable 5 |
| `studio::qa` | 独立コンテキストで動作検証・採点（合否＋差し戻し理由） | `qa::evaluate` | Opus 4.8 |
| `studio::deliver` | 成果物の確定・リポジトリ push・プレビュー公開 | `deliver::package` | Haiku 4.5 |
| `studio::orchestrator` | 全体の状態機械。各イベントを受けて次工程を起動、ループ制御 | `orch::advance` | (LLM不要 or Haiku) |

> iii らしさ: 新しい部門や能力は **`iii worker add` で後から足せる**。
> 例: `studio::security-review`, `studio::cost-estimator` を実行中に追加してラインへ差し込む。

### 2.2 Triggers（工程間の合図）

- **HTTP**: 外部からのアイデア投入口（`POST /projects`）。
- **イベント/状態変化**: `spec.ready` → `plan.ready` → `build.done` → `qa.passed|qa.failed` → `delivered`。
- **キュー**: 重い `build` はキュー投入し、ワーカーが順次処理（並列度・リトライを iii が管理）。
- **cron**(任意): 長時間ジョブの定期チェックイン/タイムアウト監視。

### 2.3 State（プロジェクト台帳）

`iii-state` に 1 プロジェクト = 1 レコード。最低限のスキーマ:

```jsonc
{
  "project_id": "prj_...",
  "idea": "ユーザーの元アイデア",
  "spec": { /* intake が確定 */ },
  "plan": { "app_type": "web-node", "tasks": [...] },
  "status": "intake|design|building|qa|revising|delivered|failed",
  "iteration": 2,
  "max_iterations": 5,
  "artifacts": { "repo_url": "...", "preview_url": "...", "files": [...] },
  "trace_id": "iii の分散トレースID",
  "history": [ /* 各工程の結果・採点・差し戻し理由 */ ]
}
```

成果物そのもの（生成コード）は state に入れず、Git / オブジェクトストレージ / Managed Agents の
セッション出力（`/mnt/session/outputs/`）に置き、参照だけを保持する。

---

## 3. 「全アプリ種別対応」 — アダプタ方式

実装ワーカー本体は**種別を知らない**。種別ごとの具体コマンドを `AppTypeAdapter` が提供する。
新種別の追加 = アダプタを 1 つ書いて登録（iii の "worker add" 哲学と一致）。

```ts
interface AppTypeAdapter {
  id: string;                 // "web-node" | "api-python" | "cli-..." | ...
  detect(spec): number;       // この種別の適合度スコア(0-1) → design が選択に使用
  scaffold(spec): Plan;       // 雛形生成手順
  buildCmd: string;           // 例: "pnpm build"
  testCmd: string;            // 例: "pnpm test"      ← QAの一次根拠
  runCmd?: string;            // 例: "pnpm preview"   ← プレビュー用
  successCheck(ctx): Rubric;  // 「動作する」の定義（テスト緑+ビルド成功+種別固有チェック）
}
```

初期アダプタ(例): `web-node`(React/Node), `api-node`, `api-python`, `cli-node`, `cli-python`。
「全種類」は**最初から全部作る**のではなく、**この契約を満たすアダプタを足していけば無限に拡張できる**
形にしておく、という意味での全対応。MVP は 1〜2 種別から。

---

## 4. 「完璧に動作する」を担保する仕組み（最重要）

魔法ではなく **生成 → 自動テスト → 不合格なら修正、を合格するまでループ**で品質を作る。
ここで Claude の **Managed Agents「Outcome」** が決定打になる:

- `studio::build` のセッションに **Outcome（成果物＋ルーブリック）** を渡す。
- ルーブリック = アダプタの `successCheck`（例: 「`testCmd` が緑」「`buildCmd` 成功」「指定エンドポイントが200」）。
- Anthropic 側が **コンテナ内で実際にコードを書き・ビルドし・テストを走らせ**、
  独立した採点モデルが各基準を採点 → 不合格なら**自動で次イテレーション**（最大 `max_iterations`）。
- 合格すると成果物が `/mnt/session/outputs/` に出る。これを `studio::deliver` が回収。

> つまり「動作するまで直し続ける QA ループ」が API ネイティブで提供される。
> iii 側はこのループを**起動・監視・トレース**し、ライン全体に組み込むのが役割。

`studio::qa` を**別途**置く構成も可能（Outcome を使わず、QAワーカーが `testCmd` を実行して
合否イベントを発行し、orchestrator が build へ差し戻す）。MVP では Outcome を使うのが最短。

---

## 5. 「コードを実際に動かす場所」の 2 案

| | 案A: iii が計算資源を持つ | 案B: Anthropic ホスト(Managed Agents) ★推奨(初期) |
|---|---|---|
| 実行場所 | iii の **sandbox / `iii-exec`** ワーカー内 | Anthropic のセッション毎コンテナ |
| 仕組み | Claude API + tool use。Claudeが bash/edit を発行→自前で実行 | Outcome ループ・GitHub リソース・出力ファイル回収まで内蔵 |
| 長所 | 完全な制御・自前インフラ・コスト管理 | **MVP最短**。生成→テスト→修正→納品が一気通貫 |
| 短所 | サンドボックス/ループ/採点を自作 | 実行環境の自由度・常時コストはAnthropic側 |

**推奨**: まず**案B**で動くものを作り、必要に応じて重い/機密な工程を**案A(iii-exec)**へ移す。
iii は両案で共通して「**オーケストレーション・カタログ・可観測性**」の背骨を担う。

> **決定（2026-06-21）: 案A（iii で自前実行）を採用。**
> 生成↔QA ループは自前（orchestrator）で構築する。詳細は [`P0-DETAIL.md`](./P0-DETAIL.md)。
>
> **「頭脳」は差し替え可能（[`BUILD-BACKENDS.md`](./BUILD-BACKENDS.md)）**:
> - **ClaudeCodeBackend（P0 既定）**: ローカルの `claude -p` を駆動。Claude Code 自身の
>   sandbox/ツール/ループと**既存ログイン認証**を再利用 → **API キー配線も従量課金も不要**で
>   「この Claude Code から」動く（本リポ環境で実証済み）。
> - **ApiBackend（将来）**: Anthropic API + 自前 tool-use ループ + 自前 sandbox（`ANTHROPIC_API_KEY` 必須）。

---

## 6. LLM 推奨（役割別・コスト最適化）

結論: **既定は Claude Opus 4.8**。役割の難易度に応じて上下に振る。
（料金は 100万トークンあたり 入力/出力, 2026-06 時点）

| モデル | ID | 料金(入/出) | 文脈 | 使いどころ |
|---|---|---|---|---|
| Claude Fable 5 | `claude-fable-5` | $10 / $50 | 1M | 最難関・大規模アプリの実装（最後の手段） |
| **Claude Opus 4.8** | `claude-opus-4-8` | $5 / $25 | 1M | **設計・実装・QA の既定**。長時間エージェント/コーディングSOTA |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | $3 / $15 | 1M | 要件ヒアリング(対話)、軽めの生成 |
| Claude Haiku 4.5 | `claude-haiku-4-5` | $1 / $5 | 200K | ルーティング/分類/納品パッケージング等の安価工程 |

役割割り当ての指針:
- **intake(対話)** → Sonnet 4.6（往復が多く、速さ/コスト重視）
- **design / build / qa** → Opus 4.8。コーディングは **effort = `xhigh`**、難所のみ Fable 5。
- **orchestrator / deliver / 分類** → Haiku 4.5。
- **コスト対策**: ① ループで不変な部分（システムプロンプト＋確定スペック）を **prompt caching** ②
  `max_iterations` で上限 ③ effort を工程別に調整。

> 補足: これは「エージェント案件」（複数ステップ・事前完全定義が困難・誤りはテストで回収可能）に
> 該当するため、単発API呼び出しではなく**エージェント構成**が妥当。実装の中核は Managed Agents、
> 各部門の判断は API + tool use、という二層が素直。

---

## 7. 可観測性（制作会社の進捗ボード）

- iii: 全 Worker/Function/Trigger を自動トレース → 「どのプロジェクトがどの工程で何回差し戻したか」可視化。
- Managed Agents: セッションのイベントストリーム＋ `usage`（トークン/コスト）を取得。
- 両者を `trace_id` / `project_id` で突き合わせ、**1案件の端から端まで**を 1 画面に。
- iii Console（このリポジトリの `console/`）をそのまま運用ダッシュボードに流用可能。

---

## 8. 安全性・ガバナンス

- **生成コードは信頼しない**: サンドボックス内でのみビルド/実行（案B=Anthropicコンテナ / 案A=iii-exec隔離）。
- **秘密情報**: Git push トークンや外部APIキーは **Vault** 経由（プロンプト/履歴に置かない）。
- **承認ゲート**: デプロイや外部公開など不可逆操作の手前に**人間承認**トリガーを差し込む（任意）。
- **コスト上限**: プロジェクト単位の `max_iterations` とトークン上限（Task Budget）でランナウェイ防止。

---

## 9. 段階的ロードマップ

| フェーズ | 目標 | 含む |
|---|---|---|
| **P0 (MVP骨格)** | アイデア→生成→自動テスト→修正→納品が **1 種別(web)** で通る | intake / design / build(Outcome) / deliver、state、HTTPトリガー |
| **P1** | QA ゲート明確化＋アダプタ 2〜3 種別、プレビューURL | qa ワーカー、adapter レジストリ、Console 連携 |
| **P2** | 並列サブエージェント、複数アプリ、承認ゲート、コスト統制 | multiagent、approval トリガー、Vault、Task Budget |
| **P3** | 自己拡張（不足機能を実行中に worker add）、テンプレ蓄積/メモリ | dynamic worker add、Memory Store |

---

## 10. 未確定事項（要決定）

1. ~~実行場所~~ → **決定: 案A(iii-exec 自前実行)**。
2. MVP の対象種別: まず `web-node` 単一でよいか。
3. 成果物の置き場: GitHub リポジトリへ push か、ローカル artifact か、プレビュー公開までやるか。
4. 予算感: 1 プロジェクトあたりの想定イテレーション/トークン上限（コスト試算の前提）。
5. Claude APIキー/権限とデータ保持設定（Fable 5 は 30日保持が必須）。

---

## 付録A: P0 のイベント定義（最小）

| イベント | 発行元 | 受信→アクション |
|---|---|---|
| `project.created` (HTTP) | 外部 | intake::clarify/spec |
| `spec.ready` | intake | design::plan |
| `plan.ready` | design | build::run（Outcome開始） |
| `build.done` | build | deliver::package（Outcome合格時） |
| `build.failed` | build | orchestrator（max_iterations超過→failed通知） |
| `delivered` | deliver | 完了通知（preview_url 返却） |
