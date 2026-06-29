# apps/arbitrage — 越境転売自動化（iii ワーカー）

国内（メルカリ/ヤフオク!/ラクマ/magi/SNKRDUNK/Amazon.co.jp）で安く仕入れ、**eBay 等の海外**で
利益が出る商品を選定 → 出品**下書き**生成 → 監視 → 記録（古物台帳）まで回す半自動システム。
**実際の仕入れ購入・最終的な出品投稿は人間**が行う（規約順守・凍結回避の意図的設計）。

> 既存 `apps/ec`（POD = オリジナル商品をAI生成して出品）とは**別事業**。共有するのは
> iii engine と `packages/contracts` のみ。Phase 0 は実 API・実投稿を行わず **Dry-run 既定**。

## 原則（マスター指示書 §3）

- 公式API優先（販売側 eBay）。国内仕入れは Playwright を最終手段に、低速・少量・ToS確認前提。
- Human-in-the-loop（投稿・購入の確定は人間）。Dry-run を先に。
- 冪等性・**在庫同期で二重販売防止**・**為替バッファ**（悲観側）・レート制限/バックオフ。
- 閾値は `config/default.yaml` に外出し（利益¥1500・利益率・間隔・FXバッファ）。

詳細は [`docs/architecture.md`](docs/architecture.md) と [`docs/compliance.md`](docs/compliance.md)。

## Phase 0 の関数

`arb::source-scan` / `arb::research-comps` / `arb::fx-rate` / `arb::profit-calc` /
`arb::evaluate` / `arb::draft-listing` / `notify::telegram` / `ledger::record` / `ledger::list`
（HTTP トリガー `/arb/*`）。

## セットアップ・コマンド（リポジトリルートから）

```bash
make install-arb     # uv venv + requirements.txt
make lint-arb        # ruff
make typecheck-arb   # mypy strict
make test-arb        # pytest（完全オフライン・Dry-run・mocked state）
bash scripts/arb-e2e.sh   # 実エンジン E2E（engine build → worker 起動 → III_E2E=1）
```

## 設定・環境変数

- `config/default.yaml`: 利益フロア・利益率・FX（base/quote/buffer/static_rate）・
  sourcing 間隔/件数・`mode.dry_run`。
- env（`.env.example` 参照）: `III_URL`、`ARB_DRY_RUN`、`FX_STATIC_RATE`、
  `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`。`.env` は**コミット禁止**。

## ディレクトリ

```
src/
  config.py            # config/default.yaml + env → Settings
  domain/models.py     # 純 dataclass（contract 対応）
  fx/calculator.py     # FX込み利益計算（純）
  sourcing/offline.py  # M1 オフライン仕入れ（fixture）
  research/offline.py  # M2 オフライン eBay 成約リサーチ（fixture）
  listing/draft.py     # M6 出品下書き（純）
  notify/telegram.py   # M9 Telegram（dry-run/未設定はプレビューのみ）
  worker/              # iii アダプタ（app/handlers/services/serializers/store/orchestration）
tests/                 # オフライン単体 + e2e（III_E2E ゲート）
```
