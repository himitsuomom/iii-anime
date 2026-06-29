"""非同期オーケストレーション関数（Phase 4）。

`pipeline::run-batch` が各商品を queue（Enqueue）へ投入し、`pipeline::run-tracked`
が処理結果を engine の state に記録、`pipeline::status` が進捗を集計する。

state は **商品ごとに別キー**で書き込む（scope=`ec-batch-items:<batch_id>`, key=index）。
read-modify-write を避けるため、queue の並列処理でも競合しない。

各ハンドラは iii.trigger 互換の `trigger` を引数で受け取り、エンジン非依存に
ユニットテストできる（offline テストは fake trigger を渡す）。
"""

import uuid
from collections.abc import Callable
from typing import Any

from src.worker.handlers import handle_pipeline_run
from src.worker.services import Services

# iii.trigger 互換: {"function_id", "payload", "action"?} を受け取り結果を返す。
TriggerFn = Callable[[dict[str, Any]], Any]

BATCH_SCOPE = "ec-batch"
QUEUE = "default"


def _items_scope(batch_id: str) -> str:
    return f"ec-batch-items:{batch_id}"


def handle_pipeline_run_batch(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`pipeline::run-batch` — products[] を queue に投入し batch_id を返す。"""
    products = data.get("products")
    if not products:
        raise ValueError("products（配列）が必要です。")

    batch_id = str(data.get("batch_id") or uuid.uuid4())
    total = len(products)

    # 合計件数を記録（status の分母）。
    trigger(
        {
            "function_id": "state::set",
            "payload": {"scope": BATCH_SCOPE, "key": batch_id, "value": {"total": total}},
        }
    )

    for index, product in enumerate(products):
        trigger(
            {
                "function_id": "pipeline::run-tracked",
                "payload": {**product, "_batch_id": batch_id, "_index": index},
                "action": {"type": "enqueue", "queue": QUEUE},
            }
        )

    return {"batch_id": batch_id, "total": total, "queued": total}


async def handle_pipeline_run_tracked(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`pipeline::run-tracked` — pipeline を実行し、結果を state（別キー）へ記録する。"""
    batch_id = data.get("_batch_id")
    index = int(data.get("_index", 0))
    payload = {k: v for k, v in data.items() if k not in ("_batch_id", "_index")}

    result = await handle_pipeline_run(payload, services)

    if batch_id is not None:
        listing = result.get("listing")
        summary = {
            "index": index,
            "success": result.get("success", False),
            "title": listing.get("title") if isinstance(listing, dict) else None,
            "error": result.get("error", ""),
        }
        trigger(
            {
                "function_id": "state::set",
                "payload": {"scope": _items_scope(str(batch_id)), "key": str(index), "value": summary},
            }
        )

    return result


def handle_pipeline_status(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`pipeline::status` — batch の進捗（completed/total/done）を集計する。"""
    batch_id = data.get("batch_id")
    if not batch_id:
        raise ValueError("batch_id が必要です。")

    meta = trigger({"function_id": "state::get", "payload": {"scope": BATCH_SCOPE, "key": str(batch_id)}})
    total = int(meta.get("total", 0)) if isinstance(meta, dict) else 0

    items = trigger({"function_id": "state::list", "payload": {"scope": _items_scope(str(batch_id))}}) or []
    completed = len(items)

    return {
        "batch_id": batch_id,
        "total": total,
        "completed": completed,
        "done": total > 0 and completed >= total,
        "items": items,
    }
