# アーキテクチャ: 越境転売アプリ（apps/arbitrage）

国内で安く仕入れ → eBay 等で利益が出るものを選定 → 出品下書き → 監視 → 記録 まで回す
半自動の越境転売支援。**調査・計算・分類・下書き生成・監視・記録**をシステムが担い、
**実際の仕入れ購入・最終的な出品投稿は人間**が行う（規約順守・凍結回避の意図的設計）。

既存 `apps/ec`（POD）とは別事業のため**別アプリ**として並行追加し、共有するのは
**iii engine** と **packages/contracts** のみ。ワーカーのレイアウト・登録方式・state 利用は
`apps/ec/src/worker/` の規約を踏襲する。

## マスター指示書 M1–M11 → 関数マップ

| Module | 関心事 | 関数（namespace） | I/O | 種別 | Phase |
|---|---|---|---|---|---|
| M1 仕入れ | 国内市場スキャン | `arb::source-scan` | `{marketplace,query,limit}` → `{candidates: SourceListing[]}` | sync | **0**（offline fixture）/ 後: Playwright |
| M2 リサーチ | eBay 成約相場 | `arb::research-comps` | `{title,keywords}` → `{comps: EbaySoldComp[], median}` | sync | **0**（offline）/ 後: eBay 公式API |
| M3 FX | 実レート＋バッファ | `arb::fx-rate` | `{base,quote,rate}` → `FxRate` | sync | **0**（static）/ 後: live feed |
| M4 利益計算 | FX込み純利益 | `arb::profit-calc` | `{sourceCost,soldPrice,fxRate,...}` → `ProfitBreakdown` | sync | **0** |
| M5 判定 | 利益¥1500/利益率ゲート | `arb::evaluate` | `{profit}` → `{decision,reasons}` | sync | **0** |
| M6 下書き | eBay 出品下書き | `arb::draft-listing` | `{sourceListing,priceUsd}` → `ListingDraft` | sync(state) | **0** |
| M7 自動投稿 | eBay 投稿 | `arb::publish-listing` | `{ListingDraft}` → `{listingId,status}` | async | 後（設計のみ） |
| M8 監視 | 成約ポーリング | `arb::monitor-sales` | cron → 成約イベント | cron | 後 |
| M9 通知 | 成約時 Telegram | `notify::telegram` | `{text,sourceUrl}` → `{ok,dryRun}` | sync | **0** |
| M10 発送 | 日本郵便 国際QR | `arb::shipment-qr` | `{orderId,address}` → `ShipmentQr` | async | 後（schema のみ） |
| M11 簿記/古物台帳 | 台帳 | `ledger::record` / `ledger::list` | `LedgerEntry` → `{ok,id}` / `{entries}` | sync(state) | **0**（記録/一覧。CSV輸出は後） |

**Phase 0 登録関数**: `arb::source-scan`・`arb::research-comps`・`arb::fx-rate`・
`arb::profit-calc`・`arb::evaluate`・`arb::draft-listing`・`notify::telegram`・
`ledger::record`・`ledger::list`。HTTPトリガー `/arb/*`（全 POST）。

## state スコープ（iii-state, KV）

| スコープ | キー | 用途 |
|---|---|---|
| `arb-candidates` | `SourceListing.id` | 仕入れ候補（冪等 upsert、後フェーズで cron 蓄積） |
| `arb-drafts` | `ListingDraft.draftId` | 出品下書き（`mode`/`status` 保持） |
| `arb-listings` | `sourceListingId` | **在庫同期 / 二重販売防止** |
| `kobutsu-ledger` | `LedgerEntry.id` | 古物台帳 |

## Dry-run / human-in-the-loop / 自動投稿 ライフサイクル

- **グローバル Dry-run**: `config/default.yaml` の `mode.dry_run`（env `ARB_DRY_RUN` で上書き）
  → `Services.dry_run`。副作用関数（`notify::telegram`、将来の `arb::publish-listing` /
  `arb::shipment-qr`）は `dry_run=True` の間、外部呼び出しをせずプレビュー/記録に留める。
  純粋関数（fx/profit/evaluate/draft 生成）は影響を受けない。
- **出品の状態機械**: `ListingDraft.mode ∈ {dry_run, human_review, auto}` ＋
  `status ∈ {draft, ready, published}`。
  - Phase 0: 常に `mode=dry_run, status=draft`（人間がコピペ投稿）。
  - human-in-the-loop: 人間が `status: draft → ready` に上げる（後: dashboard / `arb::approve-draft`）。
  - 自動投稿（M7・後フェーズ）: `mode=auto && status=ready` のものだけ
    `arb::publish-listing` が処理 → `status=published`。
  これにより**データモデルは全ライフサイクルを表現**しつつ、実装は Phase 0 の遷移だけに限定。

## FX バッファの向きと根拠（§3-6）

USD 売上を円に換算する際、**得られる円が少なくなる悲観側**に倒す:
`effective_rate = rate * (1 - bufferPercent/100)`（既定 5%）。`ProfitBreakdown.netProfit` /
`marginPercent` / `meetsFloor` はすべてこの実効レートで算出するため、¥1500 の利益フロアは
**常に悲観 FX で判定**され、レート変動で「黒字のはずが赤字」になる事故を防ぐ。

## 在庫同期 / 二重販売防止（§3-5）

中古品は基本**一点物**。`arb::draft-listing` は下書き前に `arb-listings`（`sourceListingId`
キー）を確認し、`status != cancelled` の有効な出品が既にあれば**スキップ**する。これは
`apps/ec` の冪等な `orders::ingest`（id キー upsert）の越境版。後フェーズの
`arb::monitor-sales` は eBay 成約時に `soldOnEbay=true` を立て、`notify::telegram` に
**仕入れ元 URL 付き**で通知し、人間が即購入できるようにする。

## 接続・ポート

iii engine に WebSocket（既定 `ws://localhost:49134`、compose は `ws://engine:49134`）で接続。
ワーカー名 `arbitrage-worker`。HTTP トリガーは engine の HTTP API（:3111）に `/arb/*` で公開。
SDK は `src/worker/app.py` 内で遅延 import し、ハンドラ層はエンジン非依存（オフラインテスト可）。
