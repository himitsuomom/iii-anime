"""ワーカー関数の本体（純粋: (data, services) → dict）。

エンジン非依存。state を読み書きするハンドラ（draft-listing / ledger）は trigger を取り、
store.py を介す。時刻はテスト決定性のため payload で受け取れる（無ければ現在 UTC）。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.fx.calculator import build_fx_rate, calculate_profit
from src.listing.draft import build_listing_draft
from src.research.offline import median_sold_price
from src.worker.serializers import (
    draft_to_dict,
    fx_rate_from_dict,
    fx_rate_to_dict,
    money_from_dict,
    money_to_dict,
    profit_to_dict,
    sold_comp_to_dict,
    source_listing_from_dict,
    source_listing_to_dict,
)
from src.worker.services import Services
from src.worker.store import (
    DRAFTS_SCOPE,
    LISTING_LIST_SCOPE,
    TriggerFn,
    active_listing_for_source,
    mark_listing,
    state_list,
    state_set,
)


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ts(data: dict[str, Any], key: str = "now") -> str:
    raw = data.get(key)
    return str(raw) if raw else _now_iso()


# ── M1: 仕入れスキャン ──
def handle_source_scan(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`arb::source-scan` — 国内マーケットを走査し候補を返す（Phase 0: offline fixture）。"""
    from src.domain.models import SourceMarketplace

    marketplace = SourceMarketplace(str(data.get("marketplace", "mercari")))
    query = str(data.get("query", ""))
    limit = int(data.get("limit", services.settings.sourcing.max_items_per_run))
    candidates = services.source_provider.scan(marketplace, query, limit)
    return {
        "candidates": [source_listing_to_dict(c) for c in candidates],
        "count": len(candidates),
    }


# ── M2: eBay 成約リサーチ ──
def handle_research_comps(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`arb::research-comps` — eBay 成約コンプと中央値を返す（Phase 0: offline fixture）。"""
    title = str(data.get("title", ""))
    keywords = str(data.get("keywords", ""))
    limit = int(data.get("limit", 5))
    comps = services.research.find_comps(title, keywords, limit)
    return {
        "comps": [sold_comp_to_dict(c) for c in comps],
        "median": money_to_dict(median_sold_price(comps)),
        "count": len(comps),
    }


# ── M3: 為替レート ──
def handle_fx_rate(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`arb::fx-rate` — バッファ適用済みの FxRate を返す。

    `rate` 明示時はそれを使い、無ければ FxProvider（live or 静的）に委譲する。
    """
    fx = services.settings.fx
    if data.get("rate") is not None:
        result = build_fx_rate(
            base=str(data.get("base", fx.base)),
            quote=str(data.get("quote", fx.quote)),
            rate=float(data["rate"]),
            buffer_percent=float(data.get("bufferPercent", fx.buffer_percent)),
            as_of=_ts(data, "asOf"),
            source=str(data.get("source", "override")),
        )
    else:
        result = services.fx_provider.get_rate(data.get("base"), data.get("quote"))
    return fx_rate_to_dict(result)


# ── M4: 利益計算 ──
def handle_profit_calc(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`arb::profit-calc` — FX込み純利益を ProfitBreakdown で返す。"""
    fx_cfg = services.settings.fx
    if isinstance(data.get("fxRate"), dict):
        fx = fx_rate_from_dict(data["fxRate"])
    elif data.get("rate") is not None:
        fx = build_fx_rate(
            base=fx_cfg.base,
            quote=fx_cfg.quote,
            rate=float(data["rate"]),
            buffer_percent=fx_cfg.buffer_percent,
            as_of=_ts(data, "asOf"),
        )
    else:
        fx = services.fx_provider.get_rate()
    breakdown = calculate_profit(
        source_cost=money_from_dict(data.get("sourceCost"), default_currency="JPY"),
        sold_price=money_from_dict(data.get("soldPrice"), default_currency="USD"),
        fx=fx,
        floor_jpy=services.settings.profit.floor_jpy,
        min_margin_percent=services.settings.profit.min_margin_percent,
        ebay_fee_percent=float(data.get("ebayFeePercent", 13.0)),
        payment_fee_percent=float(data.get("paymentFeePercent", 3.0)),
        shipping_jpy=int(data.get("shippingJpy", 0)),
    )
    return profit_to_dict(breakdown)


# ── M5: 判定ゲート ──
def handle_evaluate(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`arb::evaluate` — 利益フロア/利益率で出品可否を判定する。"""
    raw_profit = data.get("profit")
    profit: dict[str, Any] = raw_profit if isinstance(raw_profit, dict) else data
    net = money_from_dict(profit.get("netProfit"), default_currency="JPY")
    margin = float(profit.get("marginPercent", 0.0))
    meets_floor = bool(profit.get("meetsFloor", False))

    floor = services.settings.profit.floor_jpy
    min_margin = services.settings.profit.min_margin_percent

    reasons: list[str] = []
    if net.amount < floor:
        reasons.append(f"純利益 {net.amount}{net.currency} が下限 {floor} 未満")
    if margin < min_margin:
        reasons.append(f"利益率 {margin}% が下限 {min_margin}% 未満")

    decision = "list" if meets_floor and not reasons else "skip"
    if decision == "list":
        reasons.append(f"純利益 {net.amount}{net.currency} / 利益率 {margin}% が基準を満たす")

    return {"decision": decision, "meetsFloor": meets_floor, "reasons": reasons}


# ── M5: 国際送料の概算 ──
def handle_shipping_estimate(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`arb::shipping-estimate` — 容積/実重量の大きい方で複数キャリアの送料を比較する。"""
    from src.shipping.estimator import estimate

    return estimate(
        actual_g=int(data.get("weightG", 0)),
        length_cm=float(data.get("lengthCm", 0)),
        width_cm=float(data.get("widthCm", 0)),
        height_cm=float(data.get("heightCm", 0)),
    )


# ── M6: 出品下書き（SEO・送料・在庫同期つき・state 書き込み） ──
def handle_draft_listing(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`arb::draft-listing` — 仕入れ候補から eBay 下書きを生成し永続化する。

    keywords があれば SEO タイトル/タグを付与し、寸法/重量があれば最安送料を概算して
    説明に注記する。二重販売防止: 同一仕入れ品に有効な出品が既にあればスキップする。
    """
    from src.shipping.estimator import estimate

    source = source_listing_from_dict(data.get("sourceListing", data))
    price_usd = money_from_dict(data.get("priceUsd"), default_currency="USD")

    existing = active_listing_for_source(trigger, source.id)
    if existing is not None:
        return {
            "skipped": True,
            "reason": "既に有効な出品が存在（二重販売防止）",
            "existing": existing,
        }

    keywords_raw = data.get("keywords")
    keywords = [str(k) for k in keywords_raw] if isinstance(keywords_raw, list) else []

    shipping_note: str | None = None
    shipping: dict[str, Any] | None = None
    if data.get("weightG") is not None:
        shipping = estimate(
            actual_g=int(data.get("weightG", 0)),
            length_cm=float(data.get("lengthCm", 0)),
            width_cm=float(data.get("widthCm", 0)),
            height_cm=float(data.get("heightCm", 0)),
        )
        cheapest = shipping.get("cheapest")
        if isinstance(cheapest, dict):
            cost = cheapest.get("cost", {})
            shipping_note = (
                f"Shipping (est.): {cheapest.get('service')} ~"
                f"¥{cost.get('amount')} from Japan."
            )

    draft = build_listing_draft(
        source=source,
        price_usd=price_usd,
        created_at=_ts(data, "now"),
        keywords=keywords,
        shipping_note=shipping_note,
    )
    draft_dict = draft_to_dict(draft)
    state_set(trigger, DRAFTS_SCOPE, draft.draft_id, draft_dict)
    mark_listing(
        trigger,
        source_listing_id=source.id,
        draft_id=draft.draft_id,
        status=draft.status.value,
        url=source.url,
        title=source.title,
    )
    result: dict[str, Any] = {"skipped": False, "draft": draft_dict}
    if shipping is not None:
        result["shipping"] = shipping
    return result


# ── M1–M5 パイプライン: scan → research → fx → profit → evaluate ──
def handle_pipeline_evaluate(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`arb::pipeline-evaluate` — 仕入れ候補を一括で調査・利益判定する（read-only）。

    出品はしない。各候補について eBay 成約中央値を売価に利益計算し、フロア合格分を
    `listable` に挙げる。下書き作成（state 書き込み）は別途 `arb::draft-listing`。
    """
    from src.domain.models import SourceMarketplace

    marketplace = SourceMarketplace(str(data.get("marketplace", "mercari")))
    query = str(data.get("query", ""))
    limit = int(data.get("limit", services.settings.sourcing.max_items_per_run))
    shipping_jpy = int(data.get("shippingJpy", 0))

    candidates = services.source_provider.scan(marketplace, query, limit)
    fx = services.fx_provider.get_rate()

    results: list[dict[str, Any]] = []
    listable: list[str] = []
    for c in candidates:
        comps = services.research.find_comps(c.title)
        median = median_sold_price(comps)
        breakdown = calculate_profit(
            source_cost=c.price,
            sold_price=median,
            fx=fx,
            floor_jpy=services.settings.profit.floor_jpy,
            min_margin_percent=services.settings.profit.min_margin_percent,
            shipping_jpy=shipping_jpy,
        )
        decision = "list" if breakdown.meets_floor else "skip"
        results.append(
            {
                "sourceListing": source_listing_to_dict(c),
                "median": money_to_dict(median),
                "profit": profit_to_dict(breakdown),
                "decision": decision,
            }
        )
        if decision == "list":
            listable.append(c.id)

    return {
        "results": results,
        "count": len(results),
        "listable": listable,
        "listableCount": len(listable),
        "fxRate": fx_rate_to_dict(fx),
        "researchLive": services.research_live,
    }


# ── M4: 分類・出品リスト（state 書き込み） ──
def handle_classify(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`arb::classify` — 合格候補を価格帯×カテゴリ×PFで分類し出品リストに保存する。

    入力 `{items: [{sourceListing, profit?, category?, decision?}], onlyListable?}`。
    `onlyListable`（既定 True）なら decision==list / meetsFloor の品だけを残す。
    """
    from src.classify.classifier import price_band

    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError("classify には items 配列が必要です。")
    only_listable = bool(data.get("onlyListable", True))
    cfg = services.settings.classify

    classified: list[dict[str, Any]] = []
    by_band: dict[str, int] = {}
    by_marketplace: dict[str, int] = {}

    for item in items:
        if not isinstance(item, dict):
            continue
        source = source_listing_from_dict(item.get("sourceListing", item))
        raw_profit = item.get("profit")
        profit: dict[str, Any] = raw_profit if isinstance(raw_profit, dict) else {}
        decision = item.get("decision") or ("list" if profit.get("meetsFloor") else "skip")
        if only_listable and decision != "list":
            continue

        band = price_band(source.price.amount, cfg)
        category = str(item.get("category", "uncategorized"))
        net_profit = money_from_dict(profit.get("netProfit"), default_currency="JPY")
        entry = {
            "id": source.id,
            "marketplace": source.marketplace.value,
            "title": source.title,
            "url": source.url,
            "price": money_to_dict(source.price),
            "priceBand": band,
            "category": category,
            "decision": decision,
            "netProfitJpy": net_profit.amount,
        }
        state_set(trigger, LISTING_LIST_SCOPE, source.id, entry)
        classified.append(entry)
        by_band[band] = by_band.get(band, 0) + 1
        by_marketplace[source.marketplace.value] = by_marketplace.get(source.marketplace.value, 0) + 1

    return {
        "classified": classified,
        "count": len(classified),
        "byBand": by_band,
        "byMarketplace": by_marketplace,
    }


def handle_listing_list(
    data: dict[str, Any], services: Services, trigger: TriggerFn
) -> dict[str, Any]:
    """`arb::listing-list` — 保存済み出品リストを返す（価格帯/PFで任意フィルタ）。"""
    entries = [e for e in state_list(trigger, LISTING_LIST_SCOPE) if isinstance(e, dict)]
    band = data.get("priceBand")
    marketplace = data.get("marketplace")
    if band:
        entries = [e for e in entries if e.get("priceBand") == band]
    if marketplace:
        entries = [e for e in entries if e.get("marketplace") == marketplace]
    return {"entries": entries, "count": len(entries)}


# ── M9: 通知 ──
def handle_notify_telegram(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`notify::telegram` — Telegram 通知（dry-run/未設定時はプレビューのみ）。"""
    text = str(data.get("text", ""))
    source_url = data.get("sourceUrl")
    return services.notifier.send(text, source_url=source_url if source_url else None)
