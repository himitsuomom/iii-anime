"""オフライン仕入れプロバイダ（M1, Phase 0）。

ネットワークに触れず、決定的な fixture 候補を返す。後フェーズで Playwright ベースの
実プロバイダ（低速・少量・ToS確認前提）へ差し替える。インターフェースは
`scan(marketplace, query, limit) -> list[SourceListing]` で統一する。
"""

from __future__ import annotations

from src.domain.models import Money, SourceListing, SourceMarketplace

# 決定的な fixture。タイトルに query を反映し、件数は limit で切る。
_FIXTURE_TEMPLATES: list[tuple[str, int, str]] = [
    ("レア スニーカー 美品", 8000, "美品"),
    ("限定 トレカ PSA10", 12000, "新品同様"),
    ("ヴィンテージ 時計 稼働品", 25000, "中古"),
    ("廃盤 フィギュア 未開封", 5000, "新品"),
]


class OfflineSourceProvider:
    """fixture を返すオフライン仕入れプロバイダ。"""

    def scan(
        self,
        marketplace: SourceMarketplace,
        query: str,
        limit: int = 10,
    ) -> list[SourceListing]:
        """marketplace から query に該当する候補を最大 limit 件返す（fixture）。"""
        results: list[SourceListing] = []
        for idx, (title, price_jpy, condition) in enumerate(_FIXTURE_TEMPLATES[:limit]):
            results.append(
                SourceListing(
                    id=f"{marketplace.value}-{idx}",
                    marketplace=marketplace,
                    url=f"https://example.invalid/{marketplace.value}/item/{idx}",
                    title=f"{query} {title}".strip(),
                    price=Money(amount=price_jpy, currency="JPY"),
                    fetched_at="2026-06-29T00:00:00Z",
                    condition=condition,
                    seller_id=f"seller-{idx}",
                    image_urls=[f"https://example.invalid/img/{marketplace.value}-{idx}.jpg"],
                )
            )
        return results
