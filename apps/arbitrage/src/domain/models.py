"""越境転売のドメインモデル（純 dataclass）。

`packages/contracts/schemas/commerce.schema.json` の越境転売型に対応する。
worker/serializers.py が dict ⇄ これらの変換を担い、これら自体はエンジン非依存。
Money は最小単位（JPY なら円、USD なら... 本プロジェクトは整数円/セント運用）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SourceMarketplace(str, Enum):
    """仕入れ元（国内）マーケットプレイス。"""

    MAGI = "magi"
    SNKRDUNK = "snkrdunk"
    MERCARI = "mercari"
    YAHOO_AUCTIONS = "yahoo_auctions"
    RAKUMA = "rakuma"
    AMAZON_JP = "amazon_jp"


class ListingMode(str, Enum):
    """出品ライフサイクルのモード（Dry-run/人間確認/自動）。"""

    DRY_RUN = "dry_run"
    HUMAN_REVIEW = "human_review"
    AUTO = "auto"


class ListingStatus(str, Enum):
    """出品ステータス。Phase 0 は draft のみ生成。"""

    DRAFT = "draft"
    READY = "ready"
    PUBLISHED = "published"


class TransactionType(str, Enum):
    """古物台帳の取引種別。"""

    PURCHASE = "purchase"
    SALE = "sale"


@dataclass(frozen=True)
class Money:
    """最小単位の金額（float ドリフト回避）。"""

    amount: int
    currency: str


@dataclass(frozen=True)
class SourceListing:
    """仕入れ候補（M1）。一点物の中古品を表す。"""

    id: str
    marketplace: SourceMarketplace
    url: str
    title: str
    price: Money
    fetched_at: str
    condition: str | None = None
    seller_id: str | None = None
    image_urls: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EbaySoldComp:
    """eBay 成約済みコンプ（M2）。出品中価格でなく成約価格が主指標。"""

    item_id: str
    title: str
    sold_price: Money
    sold_at: str
    shipping_price: Money | None = None
    condition: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class FxRate:
    """為替レート＋バッファ（M3）。effectiveRate を利益計算で使う。"""

    base: str
    quote: str
    rate: float
    buffer_percent: float
    effective_rate: float
    as_of: str
    source: str = "static-config"


@dataclass(frozen=True)
class ProfitBreakdown:
    """FX込み純利益（M4）。meets_floor は buffered な effective_rate で算出。"""

    source_cost: Money
    sold_price: Money
    fx_rate: FxRate
    net_profit: Money
    margin_percent: float
    meets_floor: bool
    ebay_fee: Money | None = None
    payment_fee: Money | None = None
    shipping_cost: Money | None = None


@dataclass(frozen=True)
class ListingDraft:
    """eBay 出品下書き（M6）。mode/status が Dry-run + human-in-the-loop を表す。"""

    draft_id: str
    source_listing_id: str
    title: str
    price: Money
    mode: ListingMode
    status: ListingStatus
    created_at: str
    description: str = ""
    category_id: str | None = None
    condition: str | None = None
    image_urls: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    seo_keywords: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LedgerEntry:
    """古物台帳 / 簿記エントリ（M11）。古物営業法の帳簿項目に対応。"""

    id: str
    transaction_type: TransactionType
    item_description: str
    quantity: int
    amount: Money
    occurred_at: str
    recorded_at: str
    counterparty_name: str | None = None
    counterparty_address: str | None = None
    counterparty_verification: str | None = None
    source_url: str | None = None
