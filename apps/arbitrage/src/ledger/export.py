"""古物台帳のCSV出力と集計（M11）。純関数・副作用なし。

確定申告・古物台帳の様式に使えるCSVを生成する（§1-1, §1-4）。列は古物営業法の帳簿項目に対応。
"""

from __future__ import annotations

import csv
import io
from typing import Any

CSV_COLUMNS = [
    "id",
    "transactionType",
    "occurredAt",
    "itemDescription",
    "quantity",
    "amount",
    "currency",
    "counterpartyName",
    "counterpartyAddress",
    "sourceUrl",
]


def to_csv(entries: list[dict[str, Any]]) -> str:
    """台帳エントリ列を申告に使えるCSVテキストへ変換する。"""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for e in entries:
        amount = e.get("amount", {}) if isinstance(e.get("amount"), dict) else {}
        writer.writerow(
            {
                "id": e.get("id", ""),
                "transactionType": e.get("transactionType", ""),
                "occurredAt": e.get("occurredAt", ""),
                "itemDescription": e.get("itemDescription", ""),
                "quantity": e.get("quantity", ""),
                "amount": amount.get("amount", ""),
                "currency": amount.get("currency", ""),
                "counterpartyName": e.get("counterpartyName", ""),
                "counterpartyAddress": e.get("counterpartyAddress", ""),
                "sourceUrl": e.get("sourceUrl", ""),
            }
        )
    return buf.getvalue()


def summarize(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """購入/売却の件数と JPY 合計を集計する。"""
    purchase_count = sale_count = 0
    purchase_jpy = sale_jpy = 0
    for e in entries:
        amount = e.get("amount", {}) if isinstance(e.get("amount"), dict) else {}
        yen = int(amount.get("amount", 0)) if amount.get("currency") == "JPY" else 0
        if e.get("transactionType") == "purchase":
            purchase_count += 1
            purchase_jpy += yen
        elif e.get("transactionType") == "sale":
            sale_count += 1
            sale_jpy += yen
    return {
        "purchaseCount": purchase_count,
        "saleCount": sale_count,
        "purchaseTotalJpy": purchase_jpy,
        "saleTotalJpy": sale_jpy,
        "grossMarginJpy": sale_jpy - purchase_jpy,
    }
