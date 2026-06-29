"""非同期オーケストレーション（後フェーズ用スケルトン）。

Phase 0 では未登録。後フェーズで以下を queue / cron トリガーとして実装する:
  - `arb::source-scan` を cron（sourcing.interval_seconds 間隔）で回し候補を arb-candidates に蓄積
  - 候補ごとに research→fx→profit→evaluate をパイプライン化し、合格分だけ draft-listing
  - `arb::monitor-sales`(M8) を cron で回し、成約したら arb-listings.soldOnEbay を立てて
    `notify::telegram` に仕入れ元 URL 付きで通知（在庫同期 / 二重販売防止）

EC の orchestration.py（queue enqueue + state 追跡）と同じ非競合パターンを踏襲する予定。
"""

from __future__ import annotations

# Phase 0 では実装なし（設計のみ）。app.py はこのモジュールの関数を登録しない。
