"""ワーカーが公開するドメインサービスの組み立て。

ANTHROPIC_API_KEY の有無で本物の Claude 実装 / オフライン代替を選ぶ。
Shopify 認証情報がある場合のみ出品クライアントを生成する。すべて遅延生成で、
エンジン接続には依存しない（ユニットテスト可能）。
"""

import os
from dataclasses import dataclass
from typing import Protocol, cast

from src.analytics.demand_analyzer import DemandAnalyzer
from src.analytics.price_tracker import PriceTracker
from src.pipeline import ResalePipeline
from src.product.copyright_checker import CopyrightChecker, CopyrightCheckResult
from src.product.generator import ProductGenerator
from src.product.models import ProductInput, ProductListing
from src.worker.offline import OfflineCopyrightChecker, OfflineProductGenerator


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


def _has_anthropic_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def _has_shopify_creds() -> bool:
    return bool(
        os.environ.get("SHOPIFY_STORE_URL", "").strip()
        and os.environ.get("SHOPIFY_ACCESS_TOKEN", "").strip()
    )


def build_services(*, force_offline: bool = False) -> Services:
    """環境に応じてサービス一式を構築する。

    Args:
        force_offline: True なら API キーの有無に関わらずオフライン代替を使う
            （テスト・ローカル検証用）。
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

    shopify_client = None
    if not offline and _has_shopify_creds():
        # 出品は実認証情報がある時だけ有効化（無ければ pipeline は生成のみ実施）。
        from src.listing.shopify import ShopifyListing

        shopify_client = ShopifyListing()

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
    )
