"""需要分析モジュール。キーワードの需要スコアと推奨ニッチを算出する。"""

import statistics
from dataclasses import dataclass

from src.analytics.price_tracker import PriceTracker


@dataclass
class NicheScore:
    """キーワードのニッチスコア。"""

    keyword: str
    demand_score: float  # 0.0〜1.0（DemandSignalのtrend_scoreの平均）
    competition_level: str  # "low" | "medium" | "high"
    recommended: bool  # demand_score >= 0.6 かつ competition_level != "high"


class DemandAnalyzer:
    """需要シグナルを分析してニッチスコアを算出する。"""

    def __init__(self, tracker: PriceTracker) -> None:
        self._tracker = tracker

    def analyze_keyword(self, keyword: str) -> NicheScore:
        """keyword の DemandSignal リストから NicheScore を算出する。

        - DemandSignal が 0 件の場合: demand_score=0.0, competition_level="low", recommended=False
        - search_volume_estimate の平均が 10000 超 → "high",
          1000 超 → "medium", それ以下 → "low"
        """
        signals = self._tracker.get_demand_signals(keyword)
        if not signals:
            return NicheScore(
                keyword=keyword,
                demand_score=0.0,
                competition_level="low",
                recommended=False,
            )

        demand_score = round(statistics.mean(s.trend_score for s in signals), 10)
        avg_volume = statistics.mean(s.search_volume_estimate for s in signals)

        if avg_volume > 10000:
            competition_level = "high"
        elif avg_volume > 1000:
            competition_level = "medium"
        else:
            competition_level = "low"

        recommended = demand_score >= 0.6 and competition_level != "high"

        return NicheScore(
            keyword=keyword,
            demand_score=demand_score,
            competition_level=competition_level,
            recommended=recommended,
        )

    def rank_keywords(self, keywords: list[str]) -> list[NicheScore]:
        """複数キーワードを demand_score 降順でランク付けして返す。"""
        scores = [self.analyze_keyword(kw) for kw in keywords]
        return sorted(scores, key=lambda ns: ns.demand_score, reverse=True)

    def get_recommended_niches(self, keywords: list[str]) -> list[NicheScore]:
        """recommended=True のニッチのみを返す。"""
        return [ns for ns in self.rank_keywords(keywords) if ns.recommended]
