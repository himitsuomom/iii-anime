"""オフライン eBay リサーチ（M2, Phase 0）。

ネットワークに触れず、決定的な成約コンプ fixture を返す。後フェーズで eBay 公式
Developer API（Marketplace Insights / Browse の成約データ）へ差し替える。
出品中価格でなく**成約価格（SOLD）**を主指標にする方針を反映している。
"""

from __future__ import annotations

from statistics import median

from src.domain.models import EbaySoldComp, Money

# 決定的な成約 fixture（USD セント）。
_FIXTURE_COMPS: list[tuple[str, int, str]] = [
    ("Rare Sneakers VNDS", 18000, "2026-06-01T00:00:00Z"),
    ("Limited Trading Card PSA10", 26000, "2026-06-05T00:00:00Z"),
    ("Vintage Watch Working", 41000, "2026-06-10T00:00:00Z"),
    ("Discontinued Figure Sealed", 9000, "2026-06-12T00:00:00Z"),
    ("Rare Sneakers VNDS (2)", 20000, "2026-06-15T00:00:00Z"),
]


class OfflineEbayResearch:
    """fixture の成約コンプを返すオフライン研究プロバイダ。"""

    def find_comps(self, title: str, keywords: str = "", limit: int = 5) -> list[EbaySoldComp]:
        """title/keywords に対する成約コンプを最大 limit 件返す（fixture）。"""
        comps: list[EbaySoldComp] = []
        for idx, (comp_title, cents, sold_at) in enumerate(_FIXTURE_COMPS[:limit]):
            comps.append(
                EbaySoldComp(
                    item_id=f"ebay-sold-{idx}",
                    title=comp_title,
                    sold_price=Money(amount=cents, currency="USD"),
                    sold_at=sold_at,
                    condition="used",
                    url=f"https://example.invalid/ebay/itm/{idx}",
                )
            )
        return comps


def median_sold_price(comps: list[EbaySoldComp]) -> Money:
    """成約コンプの中央値を返す（外れ値に頑健）。空なら 0 USD。"""
    if not comps:
        return Money(amount=0, currency="USD")
    currency = comps[0].sold_price.currency
    amount = int(median(sorted(c.sold_price.amount for c in comps)))
    return Money(amount=amount, currency=currency)
