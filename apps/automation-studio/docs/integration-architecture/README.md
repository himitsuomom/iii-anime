# 統合アーキテクチャ設計: EC(couxo9) × Automation Studio

> 目的: 転売EC本体（`himitsuomom/EC` の `couxo9` ブランチ, **Python**）と、本リポジトリの
> `apps/automation-studio`（AI業務自動化, **TypeScript**）を **1つのモノレポに統合**するための設計。
>
> インタラクティブ版は同ディレクトリの **`index.html`** をブラウザで開いてください（タブ切替・図・進捗チェックリスト）。

## 1. 背景と制約

- ホスト `iii-anime` は **orchestration / 連携基盤**（worker が `namespace::function` と trigger を登録し、エンジン経由で
  TS/Python/Rust/Go を1システムに繋ぐ）。これを**統合バックボーン**に使うのが最も自然。
- **2026-06 更新**: GitHub import が認証で失敗したため EC ソースを zip で受領し、**`apps/ec/` に取り込み済み**。
  実体は **POD転売自動化パイプライン（Python 3.11, CLIバッチ）**であることが判明（下記 §11）。Web ストアフロントではない。
  → 本設計は引き続き **コントラクト中心（contract-first）**。EC を作り替えず、**薄いアダプタで iii worker 化**して差分を局所化する。

## 2. 全体方針

1. **モノレポ統合**: EC(Python) と Automation Studio(TS) を1リポジトリに同居。
2. **疎結合連携**: 両者を **iii worker** として登録し、エンジン（`ws://localhost:49134`）経由の
   **JSON over WebSocket** で相互呼び出し。同期 `trigger()` / 非同期 `TriggerAction.Enqueue({queue})` / 投げっぱなし `Void()`。
3. **単一の真実 = `packages/contracts`**: JSON Schema を正本に、TS型（`json-schema-to-typescript`）と
   Python（Pydantic, `datamodel-code-generator`）を**自動生成**して両言語で共有。

## 3. ターゲット構成

```
iii-anime/ (monorepo)
├─ engine/                         # iii ランタイム（既存）
├─ apps/
│  ├─ ec/                          # ★ EC本体(Python)= couxo9。既存サービス層 + 薄いiii workerアダプタ
│  └─ automation-studio/           # 既存(TS)。UI(Vite/React)+Honoサーバ + iii worker(ai::*)
├─ packages/
│  └─ contracts/                   # ★ 新規。JSON Schema → TS型 & Pydanticモデル（統合境界）
└─ sdk/packages/{node,python}/iii  # 両appが使う既存SDK
```

## 4. コンポーネント図

```mermaid
flowchart TB
  subgraph Browser[ブラウザ]
    UI_EC[EC ストアUI]
    UI_AS[Automation Studio UI]
  end
  subgraph Engine[iii engine ws://49134]
    Q[(Queues / Cron / State / PubSub)]
    REG[Worker & Function Registry / Tracing]
  end
  subgraph ECW[apps/ec — Python worker]
    F1[catalog::*]
    F2[orders::*]
    F3[inventory::*]
    F4[pricing::*]
  end
  subgraph ASW[apps/automation-studio — TS worker + Hono]
    A1[ai::describe-product]
    A2[ai::answer-inquiry]
    A3[ai::suggest-price]
    OFF[offline fallback / server/lib/offline.ts]
  end
  CL[(Claude API claude-opus-4-8)]
  UI_EC -->|api::method::/path| Engine
  UI_AS -->|/api -> Hono| ASW
  ECW <-->|register / trigger| Engine
  ASW <-->|register / trigger| Engine
  Engine --- Q
  Engine --- REG
  A1 -. ANTHROPIC_API_KEY .-> CL
  A2 -. fallback .-> OFF
```

## 5. 統合API（関数コントラクト）

エンジン上の関数IDは `namespace::function`（グローバル一意・worker非依存）。これが**サービス間の契約**。

関数IDは取り込んだ EC の**実モジュール**に対応付ける（下表）。

| 提供元 | 関数ID | 実モジュール（apps/ec） | 入力 → 出力 |
|---|---|---|---|
| apps/ec | `products::load` | `src/io/product_loader.py` | source(CSV等) → `ProductInput[]` |
| apps/ec | `products::describe` | `src/product/generator.py` (`ProductGenerator`) | `ProductInput` → `ProductListing` |
| apps/ec | `copyright::check` | `src/product/copyright_checker.py` | `{design_concept, name}` → `CopyrightCheckResult` |
| apps/ec | `listing::shopify` / `listing::mercari` / `listing::podtomatic` | `src/listing/*.py` | `ProductListing` → 出品結果 |
| apps/ec | `analytics::price` / `analytics::demand` | `src/analytics/{price_tracker,demand_analyzer}.py` | `{sku/keyword}` → 分析結果 |
| apps/ec | `pipeline::run` | `src/pipeline.py` (`ResalePipeline`) | `ProductInput` → `PipelineResult`（著作権→生成→出品） |
| automation-studio | `ai::describe-product` | `server/lib/offline.ts` / Claude | `DescribeRequest` → `GeneratedDescription`（キー無→テンプレ） |
| automation-studio | `ai::answer-inquiry` | `server/lib/offline.ts` / Claude | `Inquiry` → `{reply, source}`（キー無→FAQ） |

> **重複の整合（要決定・Phase 2）**: EC の `product/generator.py`（`ProductGenerator`, `claude-sonnet-4-6`）と
> automation-studio の `ai::describe-product`（`claude-opus-4-8` + オフライン代替）は**役割が重複**。
> 方針案: ECの説明生成を `ai::describe-product` の呼び出しに置換し、生成ロジックを AS に一本化（モデル/オフライン代替も統一）。
> `ai::*` は `server/lib/offline.ts` の純ロジックを再利用（キー無しでも稼働）。

## 6. 主要シーケンス

### ① 商品説明の一括生成（非同期キュー）

```mermaid
sequenceDiagram
  participant U as 運用者UI(AS)
  participant AS as automation-studio worker
  participant E as engine(queue)
  participant EC as apps/ec worker
  U->>AS: CSV/商品リストで一括出品
  AS->>E: trigger(products::load) → ProductInput[]
  E->>EC: product_loader 実行
  loop 各商品
    AS->>E: trigger(ai::describe-product, Enqueue{queue:"ai-gen"})
    E->>AS: 説明生成（Claude or テンプレ）
    AS->>E: trigger(copyright::check) → trigger(listing::shopify)
    E->>EC: 著作権チェック→出品（ResalePipeline 相当）
  end
  AS-->>U: 進捗・完了
```

### ② 問い合わせ自動応答（state / イベント駆動）

```mermaid
sequenceDiagram
  participant EC as apps/ec
  participant E as engine
  participant AS as automation-studio
  EC->>E: 新規問い合わせ（state trigger 発火）
  E->>AS: ai::answer-inquiry(inquiry)
  AS->>E: orders::get(orderId) で文脈取得
  E->>EC: 注文情報
  EC-->>AS: order
  AS->>E: 応答下書き（Claude/FAQ）→ EC へ反映 or 人間レビュー
```

### ③ KPIダッシュボードの実データ化

`apps/automation-studio/src/components/Dashboard.tsx` の `KPIS` 定数（現在モック）を、
`orders::stats` / `inventory::alerts` の `trigger()` 取得に置換する。

## 7. 横断的関心事

| 観点 | 方針 |
|---|---|
| 機密 | `ANTHROPIC_API_KEY` は **automation-studio worker のみ**保持。ブラウザ/ECには渡さない（既存方針踏襲）。 |
| 認証 | worker↔engine はプライベートNW + `InitOptions.headers` のトークン。ブラウザ→HTTPトリガーは EC既存のセッション認証。 |
| 観測性 | iii は OpenTelemetry 内蔵（`traceparent` 伝播）。`sdk/packages/{node,python}/observability` を両appで利用。 |
| 退行耐性 | AI機能はキー無しでも `offline.ts` のテンプレ/FAQで動作。EC不通時は AS 側で graceful degrade。 |
| 契約バージョン | `contracts@MAJOR` 固定・追加的変更を基本。破壊的変更は新ネームスペース（例 `catalog::v2::get`）。 |

## 8. モノレポ build / CI / deploy 統合（実構成準拠）

- **EC(Python)** `apps/ec/`: 取り込み時点では EC 由来の `requirements.txt` + setuptools + ローカル `.venv` 構成（ruff/mypy strict・line 100）。
  - ルート `Makefile` に **`install-ec` / `lint-ec` / `typecheck-ec` / `test-ec` / `ci-ec`** を追加済み（`cd apps/ec && uv ...`）。テストは外部APIをモックし**オフライン128件pass**。
  - 将来（Phase 5）: 既存 Python（`sdk/packages/python/*`）に合わせ **uv + hatchling** へパッケージング統一、`.github/workflows/ci.yml` に `ec-python-ci`（matrix 3.11+ / `engine-build`成果物 → `scripts/start-iii.sh` 起動 → pytest）を追加。
- **automation-studio(TS)**: 既存 pnpm/turbo。`iii-sdk` を `workspace:*` 依存に追加して worker 化。
- **contracts**: JSON Schema → 生成。TS型は turbo `build`（`^build` で AS が消費）、Python(Pydantic) は Makefile の codegen。
- **deploy**: engine は既存 `engine/Dockerfile`（distroless）。EC worker=Python slim+uv / AS=node をコンテナ化、
  `engine/docker-compose.yml` をローカル拡張。prod は `infra/terraform/{ec,automation-studio}` + `deploy-*.yml`（OIDC, `deploy-website.yml`に倣う）。

## 9. 段階的ロードマップ

- **Phase 0 — EC を取り込む … ✅ 完了**: zip 受領 → `apps/ec/` に取り込み済み。`make ci-ec` で **128 tests pass / ruff clean**（mypy は §11 の既知2件あり）。
- **Phase 1 — `packages/contracts`**: 代表エンティティを JSON Schema 化＋TS/Pydantic 生成（本リポに雛形あり）。実 EC モデル（`ProductInput`/`ProductListing`/`CopyrightCheckResult` 等）に合わせて項目を確定。
- **Phase 2 — EC を iii worker 化**: `apps/ec` に iii worker アダプタを追加し、`products::load` / `products::describe` / `copyright::check` / `listing::*` / `analytics::*` / `pipeline::run` を登録（ラップ対象＝`ResalePipeline`・`ProductGenerator`・`listing/*`・`analytics/*`）。説明生成の重複を `ai::describe-product` 側へ寄せるか決定。
- **Phase 3 — AS を iii worker 化**: `ai::*` を公開。Dashboard のモック値を実データに置換。
- **Phase 4 — 非同期フロー**: 一括出品・問い合わせ自動応答をキュー/stateトリガーで配線。トレース有効化。
- **Phase 5 — CI/deploy 統合**: EC を uv+hatchling へ統一、`ci.yml` に `ec-python-ci` 追加、コンテナ＆Terraform でデプロイ一本化。

## 10. 未確定事項

- **説明生成の重複整合**（EC `ProductGenerator` vs AS `ai::describe-product`、モデル `sonnet-4-6` vs `opus-4-8`）→ Phase 2 で決定。
- 「統合の物理形態」（EC を `iii-anime` に取り込む＝今回の方針 / EC 側へ集約）は最終的にユーザー確認。

## 11. 取り込み済み EC の実体（apps/ec）

POD（Print on Demand）転売自動化パイプライン（Python 3.11・CLIバッチ）。Webストアフロントではない。

- 依存: `anthropic` / `httpx` / `pydantic(+settings)` / `ShopifyAPI` / `tenacity` / `python-dotenv`。
- 主要モジュール:
  - `src/product/`: `models.py`（`ProductInput`/`ProductListing`）, `generator.py`（Claude説明生成）, `copyright_checker.py`
  - `src/listing/`: `shopify.py` / `mercari.py` / `podtomatic.py`（出品クライアント）
  - `src/analytics/`: `price_tracker.py` / `demand_analyzer.py`
  - `src/io/product_loader.py`, `src/pipeline.py`（`ResalePipeline`）, `src/config.py`
  - `scripts/`（`run_pipeline` 等）, `tests/`（**128件・外部APIを完全モック**）, `prompts/`, `data/sample_products.csv`, `docs/`
- 検証コマンド: `make ci-ec`（install→ruff→pytest）。型チェックは `make typecheck-ec`。
- **既知の課題（Phase 2 で対応）**: mypy strict で 2件のエラー（`product/generator.py`・`copyright_checker.py` の Anthropic SDK union 型 `TextBlock|ToolUseBlock` の `.text` 参照）。取り込みは原状を尊重し未修正。

---

関連: 契約スキーマの雛形は `packages/contracts/`（リポジトリルート）にあります。
