"""注文・在庫の永続化と KPI 集計（iii-state バック）。

`packages/contracts`（Order / OrderStats / InventoryItem / InventoryAlert / Money）の
dict 形をそのまま扱う。state は scope/key で**冪等に upsert**（同一 id/sku は上書き＝
重複 webhook 安全）、集計は `state::list` で全件取得して reduce する（orchestration と
同じ非競合パターン）。`trigger` は iii.trigger 互換で注入され、エンジン非依存にテストできる。
"""

from collections.abc import Callable
from typing import Any

from src.worker.services import Services

# iii.trigger 互換: {"function_id", "payload"} を受け取り結果を返す。
TriggerFn = Callable[[dict[str, Any]], Any]

ORDERS_SCOPE = "ec-orders"
INVENTORY_SCOPE = "ec-inventory"


def _normalize_money(value: Any, *, default_currency: str = "JPY") -> dict[str, Any]:
    money = value if isinstance(value, dict) else {}
    return {
        "amount": int(money.get("amount", 0)),
        "currency": str(money.get("currency", default_currency)),
    }


def _normalize_order(data: dict[str, Any]) -> dict[str, Any]:
    """webhook/手入力の dict を contract Order 形へ正規化する（id/total 必須）。"""
    order_id = str(data.get("id", "")).strip()
    if not order_id:
        raise ValueError("order.id が必要です。")
    raw_items = data.get("items") or []
    items = [
        {
            "sku": str(it.get("sku", "")),
            "quantity": int(it.get("quantity", 1)),
            "unitPrice": _normalize_money(it.get("unitPrice")),
        }
        for it in raw_items
    ]
    return {
        "id": order_id,
        "status": str(data.get("status", "pending")),
        "items": items,
        "total": _normalize_money(data.get("total")),
        "createdAt": str(data.get("createdAt", "")),
    }


def _normalize_inventory(data: dict[str, Any]) -> dict[str, Any]:
    """dict を contract InventoryItem 形へ正規化する（sku 必須）。"""
    sku = str(data.get("sku", "")).strip()
    if not sku:
        raise ValueError("inventory.sku が必要です。")
    return {
        "sku": sku,
        "onHand": int(data.get("onHand", 0)),
        "reorderPoint": int(data.get("reorderPoint", 0)),
    }


def handle_orders_ingest(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`orders::ingest` — Order を state に冪等 upsert する（重複 webhook 安全）。"""
    order = _normalize_order(data)
    trigger(
        {
            "function_id": "state::set",
            "payload": {"scope": ORDERS_SCOPE, "key": order["id"], "value": order},
        }
    )
    return {"ok": True, "id": order["id"]}


def handle_orders_stats(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`orders::stats` — 全注文を集計し OrderStats を返す。"""
    orders = trigger({"function_id": "state::list", "payload": {"scope": ORDERS_SCOPE}}) or []

    totals_by_currency: dict[str, int] = {}
    for order in orders:
        total = order.get("total") if isinstance(order, dict) else None
        money = _normalize_money(total)
        totals_by_currency[money["currency"]] = (
            totals_by_currency.get(money["currency"], 0) + money["amount"]
        )

    if totals_by_currency:
        currency = max(totals_by_currency, key=lambda c: totals_by_currency[c])
        revenue = {"amount": totals_by_currency[currency], "currency": currency}
    else:
        revenue = {"amount": 0, "currency": str(data.get("currency", "JPY"))}

    return {
        "period": str(data.get("period", "all")),
        "revenue": revenue,
        "orderCount": len(orders),
    }


def handle_inventory_upsert(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`inventory::upsert` — InventoryItem を sku キーで state に保存する。"""
    item = _normalize_inventory(data)
    trigger(
        {
            "function_id": "state::set",
            "payload": {"scope": INVENTORY_SCOPE, "key": item["sku"], "value": item},
        }
    )
    return {"ok": True, "sku": item["sku"]}


def handle_inventory_alerts(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`inventory::alerts` — 在庫が補充点以下の品を InventoryAlert[] で返す。"""
    items = trigger({"function_id": "state::list", "payload": {"scope": INVENTORY_SCOPE}}) or []

    alerts: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        on_hand = int(item.get("onHand", 0))
        reorder = int(item.get("reorderPoint", 0))
        if on_hand <= reorder:
            alerts.append(
                {
                    "sku": str(item.get("sku", "")),
                    "onHand": on_hand,
                    "severity": "out" if on_hand == 0 else "low",
                }
            )

    return {"alerts": alerts, "count": len(alerts)}
