"""実エンジン E2E テスト（Phase 0）。

`III_E2E=1` のときだけ実行する。前提:
  - iii engine が `III_URL`（既定 ws://localhost:49199）で起動済み
  - arbitrage worker（`python -m src.worker.app`）が同 engine に接続済み

1商品の手動フローを実エンジン越しに通す: source → research → fx → profit →
evaluate → draft（dry_run/draft）→ 永続確認 + Telegram dry-run プレビュー。
`scripts/arb-e2e.sh` から起動する。
"""

from __future__ import annotations

import os
import time
from typing import Any

import pytest

if not os.environ.get("III_E2E"):
    pytest.skip("III_E2E が未設定のため E2E をスキップします。", allow_module_level=True)


III_URL = os.environ.get("III_URL", "ws://localhost:49199")


@pytest.fixture(scope="module")
def client() -> Any:
    from iii import register_worker  # gate 後に import（iii SDK は E2E 実行時のみ必要）

    iii = register_worker(III_URL)
    time.sleep(2.0)  # worker 登録の伝播待ち
    yield iii
    iii.shutdown()


def test_one_item_arbitrage_flow(client: Any) -> None:
    # M1: 仕入れスキャン
    scan = client.trigger(
        {"function_id": "arb::source-scan", "payload": {"marketplace": "snkrdunk", "query": "rare", "limit": 1}}
    )
    assert scan["count"] == 1
    source = scan["candidates"][0]

    # M2: eBay 成約リサーチ
    research = client.trigger(
        {"function_id": "arb::research-comps", "payload": {"title": source["title"], "limit": 5}}
    )
    assert research["median"]["currency"] == "USD"

    # M3: 為替
    fx = client.trigger({"function_id": "arb::fx-rate", "payload": {"rate": 150.0}})
    assert fx["effectiveRate"] == 142.5

    # M4: 利益計算（成約中央値を売価に使う）
    profit = client.trigger(
        {
            "function_id": "arb::profit-calc",
            "payload": {
                "sourceCost": source["price"],
                "soldPrice": research["median"],
                "fxRate": fx,
                "shippingJpy": 1500,
            },
        }
    )
    assert profit["netProfit"]["currency"] == "JPY"

    # M5: 判定
    decision = client.trigger({"function_id": "arb::evaluate", "payload": {"profit": profit}})
    assert decision["decision"] in ("list", "skip")

    # M6: 下書き（dry_run/draft）+ 永続
    draft_out = client.trigger(
        {
            "function_id": "arb::draft-listing",
            "payload": {"sourceListing": source, "priceUsd": research["median"]},
        }
    )
    assert draft_out["skipped"] is False
    assert draft_out["draft"]["mode"] == "dry_run"
    assert draft_out["draft"]["status"] == "draft"

    # 二重販売防止: 同一品の再下書きはスキップ
    again = client.trigger(
        {
            "function_id": "arb::draft-listing",
            "payload": {"sourceListing": source, "priceUsd": research["median"]},
        }
    )
    assert again["skipped"] is True


def test_notify_dry_run(client: Any) -> None:
    out = client.trigger(
        {"function_id": "notify::telegram", "payload": {"text": "売れました", "sourceUrl": "https://x.invalid/i/1"}}
    )
    assert out["dryRun"] is True
    assert "売れました" in out["preview"]


def test_ledger_record_and_list(client: Any) -> None:
    client.trigger(
        {
            "function_id": "ledger::record",
            "payload": {
                "id": "e2e-led-1",
                "transactionType": "purchase",
                "itemDescription": "rare sneaker",
                "quantity": 1,
                "amount": {"amount": 8000, "currency": "JPY"},
                "occurredAt": "2026-06-29T00:00:00Z",
                "recordedAt": "2026-06-29T00:00:00Z",
            },
        }
    )
    listed = client.trigger({"function_id": "ledger::list", "payload": {}})
    assert listed["count"] >= 1
