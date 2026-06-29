"""発送支援: 国際発送QR（M10）。state バック。

日本郵便の国際発送（eパケット/EMS）ラベル/QRの作成を表す。実発行は公式手順・API に沿う
後段の統合点。dry_run の間は実発行せず QR ペイロードのプレビューを返す（個人情報は持たない）。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.worker.services import Services
from src.worker.store import SHIPMENTS_SCOPE, TriggerFn, state_set


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def handle_shipment_qr(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`arb::shipment-qr` — 国際発送QRを作成し保存する（dry_run はプレビューのみ）。"""
    order_id = str(data.get("orderId", "")).strip()
    if not order_id:
        raise ValueError("orderId が必要です。")
    service = str(data.get("service", "epacket"))
    shipment_id = f"ship-{order_id}"

    # 実発行は日本郵便の公式手順/APIに沿う後段統合。ここでは決定的なプレースホルダ。
    qr_payload = f"JP-POST|{service}|order={order_id}"
    record: dict[str, Any] = {
        "shipmentId": shipment_id,
        "orderId": order_id,
        "carrier": "japan_post",
        "service": service,
        "qrPayload": qr_payload,
        "createdAt": _now_iso(),
        "dryRun": services.dry_run,
    }
    state_set(trigger, SHIPMENTS_SCOPE, shipment_id, record)

    # 作成通知（dry_run なら preview のみ）。
    services.notifier.send(f"📦 発送QR作成: {service} (order {order_id})")
    return record
