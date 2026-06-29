"""eBay 公式 API による成約リサーチ（M2）。

認証情報（`EBAY_OAUTH_TOKEN`）がある時だけ実 API を叩く。無ければ services 側が
OfflineEbayResearch へ退避する（apps/ec の Shopify クライアント生成と同じゲート方式）。
出品中価格でなく**成約価格（SOLD）**を主指標にする方針。

NOTE: eBay の Marketplace Insights / Browse の正確なエンドポイント・スコープは申請条件で
変わるため、ここでは Browse API の検索を薄くラップする。実運用では公式ドキュメントの最新の
成約データ取得手段に合わせて `_endpoint` / レスポンス整形を更新すること。
"""

from __future__ import annotations

import os
from typing import Any, Protocol

from src.domain.models import EbaySoldComp, Money


class HttpClientLike(Protocol):
    def get(self, url: str, *, params: dict[str, Any], headers: dict[str, str], timeout: float) -> Any: ...


def _cents_from_value(value: Any) -> int:
    """eBay の price.value（ドル文字列）をセント整数へ。"""
    try:
        return int(round(float(value) * 100))
    except (TypeError, ValueError):
        return 0


class EbayResearchClient:
    """eBay API の成約コンプ取得（認証情報がある時のみ生成される）。"""

    def __init__(
        self,
        *,
        oauth_token: str | None = None,
        marketplace_id: str = "EBAY_US",
        http_client: HttpClientLike | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.oauth_token = oauth_token or os.environ.get("EBAY_OAUTH_TOKEN", "").strip()
        self.marketplace_id = marketplace_id
        self._http = http_client
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.oauth_token)

    def find_comps(self, title: str, keywords: str = "", limit: int = 5) -> list[EbaySoldComp]:
        """成約コンプを返す。未設定や失敗時は空リスト（services が offline へ退避）。"""
        if not self.configured:
            return []
        client = self._http
        if client is None:
            import httpx

            client = httpx
        query = f"{title} {keywords}".strip()
        try:
            resp = client.get(
                "https://api.ebay.com/buy/browse/v1/item_summary/search",
                params={"q": query, "limit": str(limit), "filter": "buyingOptions:{AUCTION|FIXED_PRICE}"},
                headers={
                    "Authorization": f"Bearer {self.oauth_token}",
                    "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:  # noqa: BLE001 — 失敗時は空（offline 退避）
            return []

        comps: list[EbaySoldComp] = []
        for item in data.get("itemSummaries", [])[:limit]:
            price = item.get("price", {})
            comps.append(
                EbaySoldComp(
                    item_id=str(item.get("itemId", "")),
                    title=str(item.get("title", "")),
                    sold_price=Money(
                        amount=_cents_from_value(price.get("value")),
                        currency=str(price.get("currency", "USD")),
                    ),
                    sold_at=str(item.get("itemEndDate", "")),
                    condition=item.get("condition"),
                    url=item.get("itemWebUrl"),
                )
            )
        return comps
