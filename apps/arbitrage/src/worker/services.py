"""ワーカーが利用するドメインサービスの組み立て。

Phase 0 はオフラインプロバイダ（fixture）で完結する。`dry_run` は副作用関数
（通知・将来の投稿/発送）の実呼び出しを抑止するフラグ。すべて遅延生成・エンジン非依存。
"""

from __future__ import annotations

from dataclasses import dataclass

from src.config import Settings, load_settings
from src.notify.telegram import TelegramNotifier
from src.research.offline import OfflineEbayResearch
from src.sourcing.offline import OfflineSourceProvider


@dataclass
class Services:
    """ワーカーが利用するサービス一式。"""

    settings: Settings
    source_provider: OfflineSourceProvider
    research: OfflineEbayResearch
    notifier: TelegramNotifier
    # 空運転。副作用関数（notify など）は True の間、実呼び出しをしない。
    dry_run: bool


def build_services(
    *,
    force_offline: bool = True,
    dry_run: bool | None = None,
    settings: Settings | None = None,
) -> Services:
    """環境に応じてサービス一式を構築する。

    Args:
        force_offline: Phase 0 では常にオフラインプロバイダ（後フェーズで実 API を選択）。
        dry_run: 明示すると settings.dry_run を上書きする（テスト用）。
        settings: 注入用（未指定なら config/default.yaml + env から読む）。
    """
    resolved = settings or load_settings()
    effective_dry_run = resolved.dry_run if dry_run is None else dry_run

    return Services(
        settings=resolved,
        source_provider=OfflineSourceProvider(),
        research=OfflineEbayResearch(),
        notifier=TelegramNotifier(dry_run=effective_dry_run),
        dry_run=effective_dry_run,
    )
