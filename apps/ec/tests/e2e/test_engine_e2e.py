"""実エンジン E2E テスト（Phase 4）。

`III_E2E=1` のときだけ実行する。前提:
  - iii engine が `III_URL`（既定 ws://localhost:49199）で起動済み
  - EC worker（`python -m src.worker.app`）が同 engine に接続済み
  - （任意）automation-studio worker が `ai::describe-product` を提供

このテストはクライアント worker として engine に接続し、登録済み関数を trigger して
sync 実行・queue 非同期・state 追跡を検証する。`scripts/ec-e2e.sh` から起動する。
"""

import os
import time
from typing import Any

import pytest

if not os.environ.get("III_E2E"):
    pytest.skip("III_E2E が未設定のため E2E をスキップします。", allow_module_level=True)

from iii import register_worker  # noqa: E402 — gate の後で import する


III_URL = os.environ.get("III_URL", "ws://localhost:49199")


def _wait_for(predicate: Any, timeout: float = 30.0, interval: float = 0.5) -> Any:
    """predicate が真値を返すまでポーリングする。"""
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval)
    return last


@pytest.fixture(scope="module")
def client() -> Any:
    iii = register_worker(III_URL)
    iii.connect()
    # worker 登録の伝播を待つ
    time.sleep(2.0)
    yield iii
    iii.shutdown()


def _product(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "category": "Mugs",
        "design_concept": "minimalist mountain",
        "target_audience": "hikers",
        "platform": "shopify",
        "language": "en",
        "niche_keywords": ["hiking", "outdoor"],
    }


def test_products_load(client: Any) -> None:
    out = client.trigger(
        {"function_id": "products::load", "payload": {"rows": [_product("A"), _product("B")]}}
    )
    assert out["count"] == 2
    assert out["products"][0]["name"] == "A"


def test_pipeline_run_sync(client: Any) -> None:
    out = client.trigger({"function_id": "pipeline::run", "payload": _product("Sync Mug")})
    # AS の ai::describe-product 経由（またはローカル退避）で生成され成功する
    assert out["success"] is True
    assert out["copyright_result"]["is_safe"] is True
    assert out["listing"] is not None
    assert out["listing"]["title"]


def test_pipeline_batch_async_with_state(client: Any) -> None:
    products = [_product(f"Batch {i}") for i in range(3)]
    started = client.trigger({"function_id": "pipeline::run-batch", "payload": {"products": products}})
    batch_id = started["batch_id"]
    assert started["total"] == 3

    def done() -> Any:
        status = client.trigger({"function_id": "pipeline::status", "payload": {"batch_id": batch_id}})
        return status if status.get("done") else None

    status = _wait_for(done, timeout=30.0)
    assert status is not None, "batch が時間内に完了しませんでした"
    assert status["completed"] == 3
    assert all(item["success"] for item in status["items"])


def test_state_roundtrip(client: Any) -> None:
    client.trigger(
        {
            "function_id": "state::set",
            "payload": {"scope": "e2e-test", "key": "k1", "value": {"hello": "world"}},
        }
    )
    got = client.trigger({"function_id": "state::get", "payload": {"scope": "e2e-test", "key": "k1"}})
    assert got == {"hello": "world"}
