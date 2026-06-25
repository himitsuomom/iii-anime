"""ワーカーが公開するドメインサービスの組み立て。

ANTHROPIC_API_KEY の有無で本物の Claude 実装 / オフライン代替を選ぶ。
Shopify 認証情報がある場合のみ出品クライアントを生成する。すべて遅延生成で、
エンジン接続には依存しない（ユニットテスト可能）。
"""

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast

from src.analytics.demand_analyzer import DemandAnalyzer
from src.analytics.price_tracker import PriceTracker
from src.pipeline import ResalePipeline
from src.product.copyright_checker import CopyrightChecker, CopyrightCheckResult
from src.product.generator import ProductGenerator
from src.product.models import ProductInput, ProductListing
from src.worker.offline import OfflineCopyrightChecker, OfflineProductGenerator

if TYPE_CHECKING:
    from src.listing.mercari import MercariListing
    from src.listing.podtomatic import PodtomaticListing
    from src.listing.shopify import ShopifyListing


class GeneratorLike(Protocol):
    """ProductGenerator / OfflineProductGenerator が満たす構造的型。"""

    def generate(self, inp: ProductInput) -> ProductListing: ...


class CheckerLike(Protocol):
    """CopyrightChecker / OfflineCopyrightChecker が満たす構造的型。"""

    def check(self, design_description: str, product_name: str) -> CopyrightCheckResult: ...


@dataclass
class Services:
    """ワーカーが利用するドメインサービス一式。"""

    generator: GeneratorLike
    checker: CheckerLike
    pipeline: ResalePipeline
    price_tracker: PriceTracker
    demand_analyzer: DemandAnalyzer
    offline: bool
    shopify_client: "ShopifyListing | None" = None
    mercari_client: "MercariListing | None" = None
    podtomatic_client: "PodtomaticListing | None" = None


def _has_anthropic_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def _has_shopify_creds() -> bool:
    return bool(
        os.environ.get("SHOPIFY_STORE_URL", "").strip()
        and os.environ.get("SHOPIFY_ACCESS_TOKEN", "").strip()
    )


def _has_mercari_creds() -> bool:
    return bool(os.environ.get("MERCARI_ACCESS_TOKEN", "").strip())


def _has_podtomatic_creds() -> bool:
    return bool(os.environ.get("PODTOMATIC_API_KEY", "").strip())


def build_services(*, force_offline: bool = False) -> Services:
    """環境に応じてサービス一式を構築する。

    Args:
        force_offline: True なら API キーの有無に関わらずオフライン代替を使う
            （テスト・ローカル検証用）。出品クライアントも生成しない。
    """
    offline = force_offline or not _has_anthropic_key()

    generator: GeneratorLike
    checker: CheckerLike
    if offline:
        generator = OfflineProductGenerator()
        checker = OfflineCopyrightChecker()
    else:
        generator = ProductGenerator()
        checker = CopyrightChecker()

    # 出品クライアントは実認証情報がある時だけ生成（無ければ None）。モジュール
    # エイリアスで遅延 import し、TYPE_CHECKING 用のクラス名を再束縛しない。
    shopify_client: ShopifyListing | None = None
    mercari_client: MercariListing | None = None
    podtomatic_client: PodtomaticListing | None = None
    if not force_offline and _has_shopify_creds():
        from src.listing import shopify as _shopify

        shopify_client = _shopify.ShopifyListing()
    if not force_offline and _has_mercari_creds():
        from src.listing import mercari as _mercari

        mercari_client = _mercari.MercariListing()
    if not force_offline and _has_podtomatic_creds():
        from src.listing import podtomatic as _podtomatic

        podtomatic_client = _podtomatic.PodtomaticListing()

    pipeline = ResalePipeline(
        generator=cast(ProductGenerator, generator),
        checker=cast(CopyrightChecker, checker),
        shopify_client=shopify_client,
    )

    price_tracker = PriceTracker()
    demand_analyzer = DemandAnalyzer(price_tracker)

    return Services(
        generator=generator,
        checker=checker,
        pipeline=pipeline,
        price_tracker=price_tracker,
        demand_analyzer=demand_analyzer,
        offline=offline,
        shopify_client=shopify_client,
        mercari_client=mercari_client,
        podtomatic_client=podtomatic_client,
    )
