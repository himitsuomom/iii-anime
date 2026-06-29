"""analyticsモジュールのテスト。PriceTracker と DemandAnalyzer を検証する。"""

import pytest

from src.analytics.demand_analyzer import DemandAnalyzer, NicheScore
from src.analytics.price_tracker import DemandSignal, PricePoint, PriceTracker

# ---- ヘルパー ----


def make_price_point(product_id: str, price: float, platform: str = "amazon") -> PricePoint:
    return PricePoint(product_id=product_id, platform=platform, price=price, currency="JPY")


def make_demand_signal(
    keyword: str,
    trend_score: float,
    search_volume: int,
    platform: str = "google",
) -> DemandSignal:
    return DemandSignal(
        keyword=keyword,
        search_volume_estimate=search_volume,
        trend_score=trend_score,
        platform=platform,
    )


# ---- TestPriceTracker ----


class TestPriceTracker:
    def test_record_price_and_get_history(self) -> None:
        tracker = PriceTracker()
        point = make_price_point("prod-1", 1000.0)
        tracker.record_price(point)
        history = tracker.get_price_history("prod-1")
        assert len(history) == 1
        assert history[0].price == 1000.0

    def test_get_price_history_filters_by_product_id(self) -> None:
        tracker = PriceTracker()
        tracker.record_price(make_price_point("prod-1", 1000.0))
        tracker.record_price(make_price_point("prod-2", 2000.0))
        history = tracker.get_price_history("prod-1")
        assert len(history) == 1
        assert history[0].product_id == "prod-1"

    def test_get_price_history_empty_for_unknown_product(self) -> None:
        tracker = PriceTracker()
        assert tracker.get_price_history("unknown") == []

    def test_suggest_price_default_margin(self) -> None:
        tracker = PriceTracker()
        # 1000 / (1 - 0.3) = 1428.57
        result = tracker.suggest_price(1000.0)
        assert result == pytest.approx(1428.57, abs=0.01)

    def test_suggest_price_custom_margin(self) -> None:
        tracker = PriceTracker()
        # 500 / (1 - 0.5) = 1000.0
        result = tracker.suggest_price(500.0, target_margin=0.5)
        assert result == 1000.0

    def test_suggest_price_raises_when_margin_is_1(self) -> None:
        """target_margin が 1.0 以上の場合に ValueError が発生すること。"""
        tracker = PriceTracker()
        with pytest.raises(ValueError, match="1.0 未満"):
            tracker.suggest_price(1000.0, target_margin=1.0)

    def test_suggest_price_with_competition_uses_lower_of_margin_and_median(self) -> None:
        tracker = PriceTracker()
        # margin_price = 1000 / 0.7 ≈ 1428.57, competitor_median = 1200.0
        result = tracker.suggest_price_with_competition(1000.0, 0.3, [1100.0, 1200.0, 1300.0])
        assert result == 1200.0

    def test_suggest_price_with_competition_uses_margin_when_competitors_higher(self) -> None:
        tracker = PriceTracker()
        # margin_price = 1000 / 0.7 ≈ 1428.57, competitor_median = 2000.0
        result = tracker.suggest_price_with_competition(1000.0, 0.3, [2000.0, 2200.0])
        assert result == pytest.approx(1428.57, abs=0.01)

    def test_suggest_price_with_competition_empty_list_returns_margin_price(self) -> None:
        tracker = PriceTracker()
        result = tracker.suggest_price_with_competition(1000.0, 0.3, [])
        assert result == pytest.approx(1428.57, abs=0.01)

    def test_get_price_statistics_returns_correct_values(self) -> None:
        tracker = PriceTracker()
        for price in [100.0, 200.0, 300.0, 400.0]:
            tracker.record_price(make_price_point("prod-1", price))
        stats = tracker.get_price_statistics("prod-1")
        assert stats["min"] == 100.0
        assert stats["max"] == 400.0
        assert stats["mean"] == pytest.approx(250.0)
        assert stats["median"] == pytest.approx(250.0)

    def test_get_price_statistics_single_point(self) -> None:
        tracker = PriceTracker()
        tracker.record_price(make_price_point("prod-1", 500.0))
        stats = tracker.get_price_statistics("prod-1")
        assert stats["min"] == 500.0
        assert stats["max"] == 500.0
        assert stats["mean"] == 500.0
        assert stats["median"] == 500.0

    def test_get_price_statistics_empty_returns_empty_dict(self) -> None:
        tracker = PriceTracker()
        stats = tracker.get_price_statistics("no-such-product")
        assert stats == {}

    def test_record_demand_signal_and_get_signals(self) -> None:
        tracker = PriceTracker()
        signal = make_demand_signal("mug", 0.8, 5000)
        tracker.record_demand_signal(signal)
        signals = tracker.get_demand_signals("mug")
        assert len(signals) == 1
        assert signals[0].trend_score == 0.8

    def test_get_demand_signals_filters_by_keyword(self) -> None:
        tracker = PriceTracker()
        tracker.record_demand_signal(make_demand_signal("mug", 0.8, 5000))
        tracker.record_demand_signal(make_demand_signal("tshirt", 0.5, 3000))
        signals = tracker.get_demand_signals("mug")
        assert len(signals) == 1
        assert signals[0].keyword == "mug"

    def test_get_demand_signals_empty_for_unknown_keyword(self) -> None:
        tracker = PriceTracker()
        assert tracker.get_demand_signals("unknown") == []


# ---- TestDemandAnalyzer ----


class TestDemandAnalyzer:
    def test_analyze_keyword_no_signals(self) -> None:
        tracker = PriceTracker()
        analyzer = DemandAnalyzer(tracker)
        result = analyzer.analyze_keyword("empty-keyword")
        assert result.demand_score == 0.0
        assert result.competition_level == "low"
        assert result.recommended is False

    def test_analyze_keyword_single_signal(self) -> None:
        tracker = PriceTracker()
        tracker.record_demand_signal(make_demand_signal("mug", 0.7, 500))
        analyzer = DemandAnalyzer(tracker)
        result = analyzer.analyze_keyword("mug")
        assert result.demand_score == pytest.approx(0.7)
        assert result.competition_level == "low"
        assert result.recommended is True

    def test_analyze_keyword_multiple_signals_avg_trend(self) -> None:
        tracker = PriceTracker()
        tracker.record_demand_signal(make_demand_signal("mug", 0.6, 500))
        tracker.record_demand_signal(make_demand_signal("mug", 0.8, 800))
        analyzer = DemandAnalyzer(tracker)
        result = analyzer.analyze_keyword("mug")
        assert result.demand_score == pytest.approx(0.7)
        assert result.competition_level == "low"
        assert result.recommended is True

    def test_analyze_keyword_competition_level_medium(self) -> None:
        tracker = PriceTracker()
        tracker.record_demand_signal(make_demand_signal("popular", 0.7, 5000))
        analyzer = DemandAnalyzer(tracker)
        result = analyzer.analyze_keyword("popular")
        assert result.competition_level == "medium"
        assert result.recommended is True

    def test_analyze_keyword_competition_level_high(self) -> None:
        tracker = PriceTracker()
        tracker.record_demand_signal(make_demand_signal("viral", 0.9, 50000))
        analyzer = DemandAnalyzer(tracker)
        result = analyzer.analyze_keyword("viral")
        assert result.competition_level == "high"
        assert result.recommended is False  # high competition → not recommended

    def test_analyze_keyword_low_demand_score_not_recommended(self) -> None:
        tracker = PriceTracker()
        tracker.record_demand_signal(make_demand_signal("niche", 0.5, 500))
        analyzer = DemandAnalyzer(tracker)
        result = analyzer.analyze_keyword("niche")
        assert result.demand_score == pytest.approx(0.5)
        assert result.recommended is False  # demand_score < 0.6

    def test_analyze_keyword_exactly_threshold_recommended(self) -> None:
        tracker = PriceTracker()
        tracker.record_demand_signal(make_demand_signal("threshold", 0.6, 500))
        analyzer = DemandAnalyzer(tracker)
        result = analyzer.analyze_keyword("threshold")
        assert result.demand_score == pytest.approx(0.6)
        assert result.recommended is True

    def test_rank_keywords_descending_order(self) -> None:
        tracker = PriceTracker()
        tracker.record_demand_signal(make_demand_signal("low", 0.3, 500))
        tracker.record_demand_signal(make_demand_signal("high", 0.9, 500))
        tracker.record_demand_signal(make_demand_signal("mid", 0.6, 500))
        analyzer = DemandAnalyzer(tracker)
        ranked = analyzer.rank_keywords(["low", "high", "mid"])
        assert ranked[0].keyword == "high"
        assert ranked[1].keyword == "mid"
        assert ranked[2].keyword == "low"

    def test_rank_keywords_empty_list(self) -> None:
        tracker = PriceTracker()
        analyzer = DemandAnalyzer(tracker)
        assert analyzer.rank_keywords([]) == []

    def test_get_recommended_niches_filters_correctly(self) -> None:
        tracker = PriceTracker()
        tracker.record_demand_signal(make_demand_signal("good", 0.8, 500))
        tracker.record_demand_signal(make_demand_signal("bad_low", 0.4, 500))
        tracker.record_demand_signal(make_demand_signal("bad_high", 0.9, 50000))
        analyzer = DemandAnalyzer(tracker)
        recommended = analyzer.get_recommended_niches(["good", "bad_low", "bad_high"])
        assert len(recommended) == 1
        assert recommended[0].keyword == "good"

    def test_get_recommended_niches_empty_when_none_qualify(self) -> None:
        tracker = PriceTracker()
        tracker.record_demand_signal(make_demand_signal("low_demand", 0.2, 500))
        analyzer = DemandAnalyzer(tracker)
        recommended = analyzer.get_recommended_niches(["low_demand"])
        assert recommended == []

    def test_niche_score_dataclass_fields(self) -> None:
        score = NicheScore(
            keyword="test",
            demand_score=0.75,
            competition_level="medium",
            recommended=True,
        )
        assert score.keyword == "test"
        assert score.demand_score == 0.75
        assert score.competition_level == "medium"
        assert score.recommended is True
