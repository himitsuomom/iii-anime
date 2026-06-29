"""ワーカーが利用するドメインサービスの組み立て。

外部認証情報の有無で実プロバイダ / オフライン代替を選ぶ（apps/ec のゲート方式に倣う）:
  - eBay リサーチ: `EBAY_OAUTH_TOKEN` があれば EbayResearchClient、無ければ OfflineEbayResearch
  - 為替: `FX_LIVE=1` なら無料 API、無ければ config 静的レート（FxProvider が内包）
`dry_run` は副作用関数（通知・将来の投稿/発送）の実呼び出しを抑止するフラグ。
すべて遅延生成・エンジン非依存（オフラインテスト可能）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from src.config import Settings, load_settings
from src.domain.models import EbaySoldComp
from src.fx.provider import FxProvider
from src.notify.telegram import TelegramNotifier
from src.research.offline import OfflineEbayResearch
from src.sourcing.offline import OfflineSourceProvider


class ResearchProvider(Protocol):
    """OfflineEbayResearch / EbayResearchClient が満たす構造的型。"""

    def find_comps(self, title: str, keywords: str = ..., limit: int = ...) -> list[EbaySoldComp]: ...


@dataclass
class Services:
    """ワーカーが利用するサービス一式。"""

    settings: Settings
    source_provider: OfflineSourceProvider
    research: ResearchProvider
    fx_provider: FxProvider
    notifier: TelegramNotifier
    # 実 eBay API を使っているか（offline 退避なら False）。
    research_live: bool
    # 空運転。副作用関数（notify など）は True の間、実呼び出しをしない。
    dry_run: bool


def _has_ebay_creds() -> bool:
    return bool(os.environ.get("EBAY_OAUTH_TOKEN", "").strip())


def build_services(
    *,
    force_offline: bool = True,
    dry_run: bool | None = None,
    settings: Settings | None = None,
) -> Services:
    """環境に応じてサービス一式を構築する。

    Args:
        force_offline: True なら認証情報があってもオフラインプロバイダを使う（テスト用）。
        dry_run: 明示すると settings.dry_run を上書きする（テスト用）。
        settings: 注入用（未指定なら config/default.yaml + env から読む）。
    """
    resolved = settings or load_settings()
    effective_dry_run = resolved.dry_run if dry_run is None else dry_run

    research: ResearchProvider
    research_live = False
    if not force_offline and _has_ebay_creds():
        from src.research.ebay import EbayResearchClient

        research = EbayResearchClient()
        research_live = True
    else:
        research = OfflineEbayResearch()

    return Services(
        settings=resolved,
        source_provider=OfflineSourceProvider(),
        research=research,
        fx_provider=FxProvider(resolved.fx, live=False if force_offline else None),
        notifier=TelegramNotifier(dry_run=effective_dry_run),
        research_live=research_live,
        dry_run=effective_dry_run,
    )
