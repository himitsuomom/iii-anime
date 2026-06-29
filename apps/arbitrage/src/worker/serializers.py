"""contract dict ⇄ ドメイン dataclass の手動マーシャリング（EC の流儀に倣う）。

`packages/contracts` の camelCase / snake_case フィールド名に厳密に合わせる。
生成 Pydantic モデルはクロス言語の正本だが、ワーカーは EC 同様 dict を手で正規化する
（エンジンとの I/O は素の dict のため）。
"""

from __future__ import annotations

from typing import Any

from src.domain.models import (
    EbaySoldComp,
    FxRate,
    LedgerEntry,
    ListingDraft,
    ListingMode,
    ListingStatus,
    Money,
    ProfitBreakdown,
    SourceListing,
    SourceMarketplace,
    TransactionType,
)


# ── Money ──
def money_to_dict(m: Money) -> dict[str, Any]:
    return {"amount": int(m.amount), "currency": m.currency}


def money_from_dict(value: Any, *, default_currency: str = "JPY") -> Money:
    raw = value if isinstance(value, dict) else {}
    return Money(
        amount=int(raw.get("amount", 0)),
        currency=str(raw.get("currency", default_currency)),
    )


# ── SourceListing ──
def source_listing_to_dict(s: SourceListing) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": s.id,
        "marketplace": s.marketplace.value,
        "url": s.url,
        "title": s.title,
        "price": money_to_dict(s.price),
        "fetchedAt": s.fetched_at,
    }
    if s.condition is not None:
        out["condition"] = s.condition
    if s.seller_id is not None:
        out["sellerId"] = s.seller_id
    if s.image_urls:
        out["imageUrls"] = list(s.image_urls)
    return out


def source_listing_from_dict(data: dict[str, Any]) -> SourceListing:
    listing_id = str(data.get("id", "")).strip()
    if not listing_id:
        raise ValueError("SourceListing.id が必要です。")
    return SourceListing(
        id=listing_id,
        marketplace=SourceMarketplace(str(data.get("marketplace", "mercari"))),
        url=str(data.get("url", "")),
        title=str(data.get("title", "")),
        price=money_from_dict(data.get("price")),
        fetched_at=str(data.get("fetchedAt", "")),
        condition=data.get("condition"),
        seller_id=data.get("sellerId"),
        image_urls=list(data.get("imageUrls", []) or []),
    )


# ── EbaySoldComp ──
def sold_comp_to_dict(c: EbaySoldComp) -> dict[str, Any]:
    out: dict[str, Any] = {
        "itemId": c.item_id,
        "title": c.title,
        "soldPrice": money_to_dict(c.sold_price),
        "soldAt": c.sold_at,
    }
    if c.shipping_price is not None:
        out["shippingPrice"] = money_to_dict(c.shipping_price)
    if c.condition is not None:
        out["condition"] = c.condition
    if c.url is not None:
        out["url"] = c.url
    return out


# ── FxRate ──
def fx_rate_to_dict(f: FxRate) -> dict[str, Any]:
    return {
        "base": f.base,
        "quote": f.quote,
        "rate": f.rate,
        "bufferPercent": f.buffer_percent,
        "effectiveRate": f.effective_rate,
        "source": f.source,
        "asOf": f.as_of,
    }


def fx_rate_from_dict(data: dict[str, Any]) -> FxRate:
    return FxRate(
        base=str(data.get("base", "USD")),
        quote=str(data.get("quote", "JPY")),
        rate=float(data.get("rate", 0.0)),
        buffer_percent=float(data.get("bufferPercent", 0.0)),
        effective_rate=float(data.get("effectiveRate", data.get("rate", 0.0))),
        as_of=str(data.get("asOf", "")),
        source=str(data.get("source", "static-config")),
    )


# ── ProfitBreakdown ──
def profit_to_dict(p: ProfitBreakdown) -> dict[str, Any]:
    out: dict[str, Any] = {
        "sourceCost": money_to_dict(p.source_cost),
        "soldPrice": money_to_dict(p.sold_price),
        "fxRate": fx_rate_to_dict(p.fx_rate),
        "netProfit": money_to_dict(p.net_profit),
        "marginPercent": p.margin_percent,
        "meetsFloor": p.meets_floor,
    }
    if p.ebay_fee is not None:
        out["ebayFee"] = money_to_dict(p.ebay_fee)
    if p.payment_fee is not None:
        out["paymentFee"] = money_to_dict(p.payment_fee)
    if p.shipping_cost is not None:
        out["shippingCost"] = money_to_dict(p.shipping_cost)
    return out


# ── ListingDraft ──
def draft_to_dict(d: ListingDraft) -> dict[str, Any]:
    out: dict[str, Any] = {
        "draftId": d.draft_id,
        "sourceListingId": d.source_listing_id,
        "title": d.title,
        "description": d.description,
        "price": money_to_dict(d.price),
        "mode": d.mode.value,
        "status": d.status.value,
        "createdAt": d.created_at,
    }
    if d.category_id is not None:
        out["categoryId"] = d.category_id
    if d.condition is not None:
        out["condition"] = d.condition
    if d.image_urls:
        out["imageUrls"] = list(d.image_urls)
    return out


def draft_from_dict(data: dict[str, Any]) -> ListingDraft:
    return ListingDraft(
        draft_id=str(data.get("draftId", "")),
        source_listing_id=str(data.get("sourceListingId", "")),
        title=str(data.get("title", "")),
        price=money_from_dict(data.get("price"), default_currency="USD"),
        mode=ListingMode(str(data.get("mode", "dry_run"))),
        status=ListingStatus(str(data.get("status", "draft"))),
        created_at=str(data.get("createdAt", "")),
        description=str(data.get("description", "")),
        category_id=data.get("categoryId"),
        condition=data.get("condition"),
        image_urls=list(data.get("imageUrls", []) or []),
    )


# ── LedgerEntry ──
def ledger_to_dict(e: LedgerEntry) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": e.id,
        "transactionType": e.transaction_type.value,
        "itemDescription": e.item_description,
        "quantity": int(e.quantity),
        "amount": money_to_dict(e.amount),
        "occurredAt": e.occurred_at,
        "recordedAt": e.recorded_at,
    }
    for key, val in (
        ("counterpartyName", e.counterparty_name),
        ("counterpartyAddress", e.counterparty_address),
        ("counterpartyVerification", e.counterparty_verification),
        ("sourceUrl", e.source_url),
    ):
        if val is not None:
            out[key] = val
    return out


def ledger_from_dict(data: dict[str, Any]) -> LedgerEntry:
    entry_id = str(data.get("id", "")).strip()
    if not entry_id:
        raise ValueError("LedgerEntry.id が必要です。")
    return LedgerEntry(
        id=entry_id,
        transaction_type=TransactionType(str(data.get("transactionType", "purchase"))),
        item_description=str(data.get("itemDescription", "")),
        quantity=int(data.get("quantity", 1)),
        amount=money_from_dict(data.get("amount")),
        occurred_at=str(data.get("occurredAt", "")),
        recorded_at=str(data.get("recordedAt", "")),
        counterparty_name=data.get("counterpartyName"),
        counterparty_address=data.get("counterpartyAddress"),
        counterparty_verification=data.get("counterpartyVerification"),
        source_url=data.get("sourceUrl"),
    )
