"""価格追跡・需要予測モジュール。

実装フェーズでは httpx + BeautifulSoup / 競合API を使って
リアルタイム価格監視と需要予測スコアを算出する。
"""

import statistics
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PricePoint:
    """競合商品の価格データポイント。"""

    product_id: str
    platform: str
    price: float
    currency: str
    recorded_at: datetime = field(default_factory=datetime.now)
    competitor_url: str = ""


@dataclass
class DemandSignal:
    """需要シグナル（検索ボリューム・トレンドスコア等）。"""

    keyword: str
    search_volume_estimate: int
    trend_score: float  # 0.0〜1.0
    platform: str
    recorded_at: datetime = field(default_factory=datetime.now)


class PriceTracker:
    """価格追跡・需要予測のインターフェース。

    - Amazon BSR（ベストセラーランク）からの需要推定
    - Shopify店舗の競合価格スクレイピング
    - 最適価格算出ロジック（原価 + マージン + 競合価格の中央値）
    """

    def __init__(self) -> None:
        self._price_history: list[PricePoint] = []
        self._demand_signals: list[DemandSignal] = []

    def record_price(self, point: PricePoint) -> None:
        """価格データポイントを記録する。"""
        self._price_history.append(point)

    def get_price_history(self, product_id: str) -> list[PricePoint]:
        """指定商品の価格履歴を返す。"""
        return [p for p in self._price_history if p.product_id == product_id]

    def suggest_price(self, cost: float, target_margin: float = 0.3) -> float:
        """原価とターゲット利益率から推奨価格を計算する（シンプル版）。"""
        if target_margin >= 1.0:
            raise ValueError(f"target_margin は 1.0 未満にしてください（現在: {target_margin}）")
        return round(cost / (1 - target_margin), 2)

    def suggest_price_with_competition(
        self,
        cost: float,
        target_margin: float,
        competitor_prices: list[float],
    ) -> float:
        """競合価格も考慮した最適価格を算出する。

        原価マージン価格と競合中央値を比較し、低い方を推奨価格として返す。
        競合価格リストが空の場合は原価マージン価格のみで計算する。
        """
        margin_price = self.suggest_price(cost, target_margin)
        if not competitor_prices:
            return margin_price
        competitor_median = statistics.median(competitor_prices)
        return round(min(margin_price, competitor_median), 2)

    def get_price_statistics(self, product_id: str) -> dict[str, float]:
        """記録済みの価格履歴から統計（min/max/mean/median）を返す。

        product_id の価格履歴が存在しない場合は空辞書を返す。
        """
        history = self.get_price_history(product_id)
        if not history:
            return {}
        prices = [p.price for p in history]
        return {
            "min": min(prices),
            "max": max(prices),
            "mean": statistics.mean(prices),
            "median": statistics.median(prices),
        }

    def record_demand_signal(self, signal: DemandSignal) -> None:
        """需要シグナルを記録する。"""
        self._demand_signals.append(signal)

    def get_demand_signals(self, keyword: str) -> list[DemandSignal]:
        """指定キーワードの需要シグナル一覧を返す。"""
        return [s for s in self._demand_signals if s.keyword == keyword]
