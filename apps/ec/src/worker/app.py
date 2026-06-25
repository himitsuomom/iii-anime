"""apps/ec を iii ワーカーとして登録するエントリポイント（Phase 2 アダプタ）。

設計書（apps/automation-studio/docs/integration-architecture）の関数コントラクトを
実モジュールに束ねる薄い層。`iii` SDK のインポートはこのファイル内に閉じてあり、
ハンドラ・サービス・シリアライザはエンジン非依存（オフラインでテスト可能）。

起動:
    III_URL=ws://localhost:49134 python -m src.worker.app
キーが無い環境ではオフライン代替で稼働する（説明生成・著作権チェック）。
"""

import os
from collections.abc import Awaitable, Callable
from typing import Any

from src.worker.handlers import (
    handle_analytics_demand,
    handle_analytics_price,
    handle_copyright_check,
    handle_describe,
    handle_list_mercari,
    handle_list_podtomatic,
    handle_list_shopify,
    handle_pipeline_run,
    handle_products_load,
)
from src.worker.orchestration import (
    handle_pipeline_run_batch,
    handle_pipeline_run_tracked,
    handle_pipeline_status,
)
from src.worker.services import Services, build_services

# 関数ID → (同期ハンドラ, HTTP パス)。HTTP メソッドはすべて POST。
SyncHandler = Callable[[dict[str, Any], Services], dict[str, Any]]
AsyncHandler = Callable[[dict[str, Any], Services], Awaitable[dict[str, Any]]]

SYNC_FUNCTIONS: list[tuple[str, SyncHandler, str]] = [
    ("products::describe", handle_describe, "/ec/describe"),
    ("products::load", handle_products_load, "/ec/products/load"),
    ("copyright::check", handle_copyright_check, "/ec/copyright-check"),
    ("analytics::price", handle_analytics_price, "/ec/analytics/price"),
    ("analytics::demand", handle_analytics_demand, "/ec/analytics/demand"),
]

ASYNC_FUNCTIONS: list[tuple[str, AsyncHandler, str]] = [
    ("pipeline::run", handle_pipeline_run, "/ec/pipeline/run"),
    ("listing::shopify", handle_list_shopify, "/ec/list/shopify"),
    ("listing::mercari", handle_list_mercari, "/ec/list/mercari"),
    ("listing::podtomatic", handle_list_podtomatic, "/ec/list/podtomatic"),
]


def _unwrap_payload(data: dict[str, Any]) -> dict[str, Any]:
    """trigger() の生 payload と HTTP の ApiRequest 形式の両方を受け付ける。

    ApiRequest 形（body + method/headers/path_params を持つ）なら body を取り出し、
    そうでなければそのままドメイン payload として扱う。
    """
    if isinstance(data, dict) and "body" in data and (
        "method" in data or "headers" in data or "path_params" in data
    ):
        body = data.get("body")
        return body if isinstance(body, dict) else {}
    return data


def register_ec_functions(iii: Any, services: Services) -> None:
    """エンジンインスタンス iii にEC関数群とHTTPトリガーを登録する。

    `iii` は型注釈上 Any（SDK 非依存を保つため）だが、実体は III インスタンス。
    """
    for function_id, sync_handler, api_path in SYNC_FUNCTIONS:

        def make_sync(h: SyncHandler) -> Callable[[dict[str, Any]], dict[str, Any]]:
            def wrapper(data: dict[str, Any]) -> dict[str, Any]:
                return h(_unwrap_payload(data), services)

            return wrapper

        iii.register_function(function_id, make_sync(sync_handler))
        iii.register_trigger(
            {
                "type": "http",
                "function_id": function_id,
                "config": {"api_path": api_path, "http_method": "POST"},
            }
        )

    for function_id, async_handler, api_path in ASYNC_FUNCTIONS:

        def make_async(
            h: AsyncHandler,
        ) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]:
            async def wrapper(data: dict[str, Any]) -> dict[str, Any]:
                return await h(_unwrap_payload(data), services)

            return wrapper

        iii.register_function(function_id, make_async(async_handler))
        iii.register_trigger(
            {
                "type": "http",
                "function_id": function_id,
                "config": {"api_path": api_path, "http_method": "POST"},
            }
        )


def register_ec_orchestration(iii: Any, services: Services) -> None:
    """非同期オーケストレーション関数を登録する（iii.trigger を内部で利用する）。

    `pipeline::run-batch` / `pipeline::status` は HTTP トリガー付き。
    `pipeline::run-tracked` は queue 専用（内部用）なので HTTP トリガーは付けない。
    """
    trigger = iii.trigger

    def run_batch(data: dict[str, Any]) -> dict[str, Any]:
        return handle_pipeline_run_batch(_unwrap_payload(data), services, trigger)

    def status(data: dict[str, Any]) -> dict[str, Any]:
        return handle_pipeline_status(_unwrap_payload(data), services, trigger)

    async def run_tracked(data: dict[str, Any]) -> dict[str, Any]:
        return await handle_pipeline_run_tracked(_unwrap_payload(data), services, trigger)

    iii.register_function("pipeline::run-batch", run_batch)
    iii.register_trigger(
        {
            "type": "http",
            "function_id": "pipeline::run-batch",
            "config": {"api_path": "/ec/pipeline/run-batch", "http_method": "POST"},
        }
    )
    iii.register_function("pipeline::status", status)
    iii.register_trigger(
        {
            "type": "http",
            "function_id": "pipeline::status",
            "config": {"api_path": "/ec/pipeline/status", "http_method": "POST"},
        }
    )
    iii.register_function("pipeline::run-tracked", run_tracked)


def main() -> None:
    """ワーカーを起動してエンジンに接続し、常駐する。"""
    from iii import register_worker  # 遅延 import: SDK 非依存を保つ

    url = os.environ.get("III_URL", "ws://localhost:49134")
    iii = register_worker(url)

    # 説明生成は既定で remote（automation-studio の ai::describe-product / opus）へ
    # 一本化し、失敗時はローカル/オフラインへ退避する。EC_DESCRIBE_BACKEND=local で
    # 従来のローカル生成に固定できる。
    use_remote = os.environ.get("EC_DESCRIBE_BACKEND", "remote").lower() != "local"
    services = build_services(describe_trigger=iii.trigger if use_remote else None)

    describe_mode = "remote ai::describe-product (opus)" if use_remote else "local"
    base_mode = "offline (no ANTHROPIC_API_KEY)" if services.offline else "live (Claude API)"
    print(f"[ec-worker] connecting to {url} — describe: {describe_mode}, local-fallback: {base_mode}")

    register_ec_functions(iii, services)
    register_ec_orchestration(iii, services)
    iii.connect()
    registered = [fid for fid, _, _ in SYNC_FUNCTIONS] + [fid for fid, _, _ in ASYNC_FUNCTIONS]
    registered += ["pipeline::run-batch", "pipeline::status", "pipeline::run-tracked"]
    print(f"[ec-worker] registered: {', '.join(registered)}")

    try:
        # 接続スレッドを生かしたまま常駐する。
        import threading

        threading.Event().wait()
    except KeyboardInterrupt:
        iii.shutdown()


if __name__ == "__main__":
    main()
