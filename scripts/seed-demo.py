"""ローカルデモ用シード。

サンプルの注文/在庫を engine に投入し、`orders::stats` / `inventory::alerts` の
集計結果を表示する。実 Shopify ストアが無くても Dashboard が実データを表示できる。

前提: iii engine 起動済み・EC worker 接続済み（`scripts/ec-e2e.sh` または
`make engine-up` ＋ `python -m src.worker.app`）。`make seed-demo` から実行する。
"""

import os

from iii import register_worker

III_URL = os.environ.get("III_URL", "ws://localhost:49199")

_ORDER_AMOUNTS = [1200, 2480, 980, 3600, 1500]
ORDERS = [
    {
        "id": f"demo-{i}",
        "status": "paid",
        "items": [{"sku": "MUG-1", "quantity": 1, "unitPrice": {"amount": amount, "currency": "JPY"}}],
        "total": {"amount": amount, "currency": "JPY"},
        "createdAt": "2026-06-26T00:00:00Z",
    }
    for i, amount in enumerate(_ORDER_AMOUNTS, start=1)
]

INVENTORY = [
    {"sku": "MUG-1", "onHand": 2, "reorderPoint": 5},  # low
    {"sku": "TEE-1", "onHand": 0, "reorderPoint": 3},  # out
    {"sku": "CAP-1", "onHand": 40, "reorderPoint": 10},  # ok
]


def main() -> None:
    iii = register_worker(III_URL)
    try:
        for order in ORDERS:
            iii.trigger({"function_id": "orders::ingest", "payload": order})
        for item in INVENTORY:
            iii.trigger({"function_id": "inventory::upsert", "payload": item})

        stats = iii.trigger({"function_id": "orders::stats", "payload": {}})
        alerts = iii.trigger({"function_id": "inventory::alerts", "payload": {}})
        print(f"[seed-demo] seeded {len(ORDERS)} orders, {len(INVENTORY)} inventory items")
        print(f"[seed-demo] orders::stats   => {stats}")
        print(f"[seed-demo] inventory::alerts => {alerts}")
    finally:
        iii.shutdown()


if __name__ == "__main__":
    main()
