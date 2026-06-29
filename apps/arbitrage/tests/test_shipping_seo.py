"""Phase 3: 送料概算・SEO・下書き拡充のテスト（オフライン）。"""

from __future__ import annotations

from typing import Any

import pytest

from src.listing.seo import build_seo_title, build_tags
from src.shipping.estimator import chargeable_weight_g, estimate, volumetric_weight_g
from src.worker.handlers import handle_draft_listing, handle_shipping_estimate
from src.worker.services import Services, build_services


class _FakeStateEngine:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], Any] = {}

    def trigger(self, req: dict[str, Any]) -> Any:
        fid = req["function_id"]
        p = req.get("payload", {})
        if fid == "state::set":
            self.store[(p["scope"], p["key"])] = p["value"]
            return {"new_value": p["value"]}
        if fid == "state::get":
            return self.store.get((p["scope"], p["key"]))
        if fid == "state::list":
            return [v for (s, _), v in self.store.items() if s == p["scope"]]
        raise AssertionError(fid)


@pytest.fixture
def services() -> Services:
    return build_services(force_offline=True, dry_run=True)


# ── shipping ──
def test_volumetric_vs_actual_takes_larger() -> None:
    # 30x20x10 cm = 6000 cm^3 → 1200 g volumetric > 500 g actual.
    assert volumetric_weight_g(30, 20, 10) == 1200
    assert chargeable_weight_g(500, 30, 20, 10) == 1200
    # heavy actual wins.
    assert chargeable_weight_g(3000, 30, 20, 10) == 3000


def test_estimate_picks_cheapest_eligible() -> None:
    out = estimate(actual_g=500)
    assert out["chargeableWeightG"] == 500
    assert out["cheapest"]["service"] == "small_packet_air"  # cheapest base+per_g at 500g
    # heavy item exceeds 2kg services → only EMS eligible.
    heavy = estimate(actual_g=5000)
    assert heavy["cheapest"]["service"] == "ems"


def test_shipping_estimate_handler(services: Services) -> None:
    out = handle_shipping_estimate({"weightG": 800, "lengthCm": 20, "widthCm": 15, "heightCm": 10}, services)
    # volumetric 20*15*10/5000*1000 = 600 < 800 actual → chargeable 800
    assert out["chargeableWeightG"] == 800
    assert out["cheapest"] is not None


# ── SEO ──
def test_seo_title_weaves_keywords_within_limit() -> None:
    title = build_seo_title("Sneaker", ["rare", "vintage", "japan"])
    assert "rare" in title
    assert len(title) <= 80


def test_seo_title_skips_duplicates() -> None:
    title = build_seo_title("Rare Sneaker", ["rare", "limited"])
    # 'rare' already present (case-insensitive) → not duplicated
    assert title.lower().count("rare") == 1


def test_build_tags_dedups() -> None:
    tags = build_tags(["a", "A", "b", "", " c "])
    assert tags == ["a", "b", "c"]


# ── draft enrichment ──
def test_draft_listing_with_seo_and_shipping(services: Services) -> None:
    engine = _FakeStateEngine()
    out = handle_draft_listing(
        {
            "sourceListing": {
                "id": "snkrdunk-9",
                "marketplace": "snkrdunk",
                "url": "https://x.invalid/9",
                "title": "Sneaker",
                "price": {"amount": 8000, "currency": "JPY"},
                "fetchedAt": "2026-06-29T00:00:00Z",
            },
            "priceUsd": {"amount": 20000, "currency": "USD"},
            "keywords": ["rare", "vintage"],
            "weightG": 900,
            "now": "t",
        },
        services,
        engine.trigger,
    )
    assert out["skipped"] is False
    assert "rare" in out["draft"]["title"]
    assert out["draft"]["tags"] == ["rare", "vintage"]
    assert out["shipping"]["cheapest"] is not None
    assert "Shipping (est.)" in out["draft"]["description"]
