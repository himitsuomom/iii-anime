"""apps/arbitrage を iii ワーカーとして登録するエントリポイント（Phase 0）。

越境転売（国内仕入れ→eBay転売）の調査・計算・下書き生成・通知・古物台帳を関数として束ねる
薄い層。`iii` SDK のインポートはこのファイル内に閉じてあり、ハンドラ・サービスはエンジン
非依存（オフラインでテスト可能）。Phase 0 は実 API・実投稿を行わず Dry-run 既定で稼働する。

起動:
    III_URL=ws://localhost:49134 python -m src.worker.app
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from src.worker.handlers import (
    handle_draft_listing,
    handle_evaluate,
    handle_fx_rate,
    handle_notify_telegram,
    handle_pipeline_evaluate,
    handle_profit_calc,
    handle_research_comps,
    handle_source_scan,
)
from src.worker.services import Services, build_services
from src.worker.store import (
    TriggerFn,
    handle_ledger_list,
    handle_ledger_record,
)

# 関数ID → (ハンドラ, HTTP パス)。HTTP メソッドはすべて POST。
SyncHandler = Callable[[dict[str, Any], Services], dict[str, Any]]
StoreHandler = Callable[[dict[str, Any], Services, TriggerFn], dict[str, Any]]
LedgerHandler = Callable[[dict[str, Any], TriggerFn], dict[str, Any]]

# 純粋 sync（state を触らない）。
SYNC_FUNCTIONS: list[tuple[str, SyncHandler, str]] = [
    ("arb::source-scan", handle_source_scan, "/arb/source/scan"),
    ("arb::research-comps", handle_research_comps, "/arb/research/comps"),
    ("arb::fx-rate", handle_fx_rate, "/arb/fx/rate"),
    ("arb::profit-calc", handle_profit_calc, "/arb/profit/calc"),
    ("arb::pipeline-evaluate", handle_pipeline_evaluate, "/arb/pipeline/evaluate"),
    ("arb::evaluate", handle_evaluate, "/arb/evaluate"),
    ("notify::telegram", handle_notify_telegram, "/arb/notify"),
]

# state を読み書きする sync（trigger 注入。専用スレッドで実行されるため sync trigger 可）。
STORE_FUNCTIONS: list[tuple[str, StoreHandler, str]] = [
    ("arb::draft-listing", handle_draft_listing, "/arb/draft"),
]

# 古物台帳（trigger のみ・services 不要）。
LEDGER_FUNCTIONS: list[tuple[str, LedgerHandler, str]] = [
    ("ledger::record", handle_ledger_record, "/arb/ledger/record"),
    ("ledger::list", handle_ledger_list, "/arb/ledger/list"),
]


def _unwrap_payload(data: dict[str, Any]) -> dict[str, Any]:
    """trigger() の生 payload と HTTP の ApiRequest 形式の両方を受け付ける。"""
    if isinstance(data, dict) and "body" in data and (
        "method" in data or "headers" in data or "path_params" in data
    ):
        body = data.get("body")
        return body if isinstance(body, dict) else {}
    return data


def _http_trigger(function_id: str, api_path: str) -> dict[str, Any]:
    return {
        "type": "http",
        "function_id": function_id,
        "config": {"api_path": api_path, "http_method": "POST"},
    }


def register_arbitrage_functions(iii: Any, services: Services) -> None:
    """エンジンインスタンス iii に越境転売関数群と HTTP トリガーを登録する。"""
    trigger = iii.trigger

    for function_id, sync_handler, api_path in SYNC_FUNCTIONS:

        def make_sync(h: SyncHandler) -> Callable[[dict[str, Any]], dict[str, Any]]:
            def wrapper(data: dict[str, Any]) -> dict[str, Any]:
                return h(_unwrap_payload(data), services)

            return wrapper

        iii.register_function(function_id, make_sync(sync_handler))
        iii.register_trigger(_http_trigger(function_id, api_path))

    for function_id, store_handler, api_path in STORE_FUNCTIONS:

        def make_store(h: StoreHandler) -> Callable[[dict[str, Any]], dict[str, Any]]:
            def wrapper(data: dict[str, Any]) -> dict[str, Any]:
                return h(_unwrap_payload(data), services, trigger)

            return wrapper

        iii.register_function(function_id, make_store(store_handler))
        iii.register_trigger(_http_trigger(function_id, api_path))

    for function_id, ledger_handler, api_path in LEDGER_FUNCTIONS:

        def make_ledger(h: LedgerHandler) -> Callable[[dict[str, Any]], dict[str, Any]]:
            def wrapper(data: dict[str, Any]) -> dict[str, Any]:
                return h(_unwrap_payload(data), trigger)

            return wrapper

        iii.register_function(function_id, make_ledger(ledger_handler))
        iii.register_trigger(_http_trigger(function_id, api_path))


def registered_function_ids() -> list[str]:
    """登録される関数 ID 一覧（起動ログ用）。"""
    ids = [fid for fid, _, _ in SYNC_FUNCTIONS]
    ids += [fid for fid, _, _ in STORE_FUNCTIONS]
    ids += [fid for fid, _, _ in LEDGER_FUNCTIONS]
    return ids


def main() -> None:
    """ワーカーを起動してエンジンに接続し、常駐する。"""
    from iii import InitOptions, register_worker  # 遅延 import: SDK 非依存を保つ

    url = os.environ.get("III_URL", "ws://localhost:49134")
    otel_enabled = os.environ.get("III_TELEMETRY_ENABLED", "").lower() != "false"
    iii = register_worker(
        url,
        InitOptions(
            worker_name="arbitrage-worker",
            otel={"enabled": otel_enabled, "service_name": "arbitrage-worker"},
        ),
    )

    services = build_services()
    mode = "DRY-RUN" if services.dry_run else "LIVE"
    print(f"[arbitrage-worker] connecting to {url} — mode: {mode}")

    register_arbitrage_functions(iii, services)
    print(f"[arbitrage-worker] registered: {', '.join(registered_function_ids())}")

    try:
        import threading

        threading.Event().wait()
    except KeyboardInterrupt:
        iii.shutdown()


if __name__ == "__main__":
    main()
