"""Phase 1: FX プロバイダ・eBay クライアント・評価パイプラインのテスト（オフライン）。"""

from __future__ import annotations

from typing import Any

import pytest

from src.config import load_settings
from src.fx.provider import FxProvider
from src.research.ebay import EbayResearchClient
from src.worker.handlers import handle_pipeline_evaluate
from src.worker.services import Services, build_services


@pytest.fixture
def services() -> Services:
    return build_services(force_offline=True, dry_run=True)


# ── FxProvider ──
def test_fx_provider_static_default() -> None:
    fx_cfg = load_settings().fx
    provider = FxProvider(fx_cfg, live=False)
    rate = provider.get_rate()
    assert rate.source == "static-config"
    assert rate.effective_rate == fx_cfg.static_rate * (1 - fx_cfg.buffer_percent / 100)


class _FakeResp:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeHttp:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.called = False

    def get(
        self,
        url: str,
        *,
        params: dict[str, Any],
        timeout: float,
        headers: dict[str, str] | None = None,
    ) -> _FakeResp:
        self.called = True
        return _FakeResp(self._payload)


def test_fx_provider_live_uses_api_then_buffers() -> None:
    fx_cfg = load_settings().fx
    http = _FakeHttp({"rates": {"JPY": 160.0}})
    provider = FxProvider(fx_cfg, live=True, http_client=http)
    rate = provider.get_rate("USD", "JPY")
    assert http.called is True
    assert rate.rate == 160.0
    assert rate.source == "exchangerate.host"
    assert rate.effective_rate == 160.0 * (1 - fx_cfg.buffer_percent / 100)


def test_fx_provider_live_failure_falls_back() -> None:
    fx_cfg = load_settings().fx

    class _BoomHttp:
        def get(self, url: str, *, params: dict[str, Any], timeout: float) -> Any:
            raise RuntimeError("network down")

    provider = FxProvider(fx_cfg, live=True, http_client=_BoomHttp())
    rate = provider.get_rate()
    assert rate.source == "static-config"
    assert rate.rate == fx_cfg.static_rate


# ── EbayResearchClient ──
def test_ebay_client_unconfigured_returns_empty() -> None:
    client = EbayResearchClient(oauth_token="")
    assert client.configured is False
    assert client.find_comps("anything") == []


def test_ebay_client_parses_summaries() -> None:
    payload = {
        "itemSummaries": [
            {
                "itemId": "v1|123|0",
                "title": "Rare Sneaker",
                "price": {"value": "180.00", "currency": "USD"},
                "itemEndDate": "2026-06-01T00:00:00Z",
                "condition": "Used",
                "itemWebUrl": "https://ebay.example/itm/123",
            }
        ]
    }
    client = EbayResearchClient(oauth_token="tok", http_client=_FakeHttp(payload))  # type: ignore[arg-type]
    comps = client.find_comps("sneaker", limit=5)
    assert len(comps) == 1
    assert comps[0].sold_price.amount == 18000  # cents
    assert comps[0].sold_price.currency == "USD"


# ── pipeline-evaluate ──
def test_pipeline_evaluate_returns_results_and_listable(services: Services) -> None:
    out = handle_pipeline_evaluate(
        {"marketplace": "snkrdunk", "query": "rare", "limit": 4, "shippingJpy": 1500}, services
    )
    assert out["count"] == 4
    assert out["researchLive"] is False
    assert out["fxRate"]["effectiveRate"] > 0
    # 各結果は decision を持ち、listable は list 判定の id 集合。
    for r in out["results"]:
        assert r["decision"] in ("list", "skip")
        assert "profit" in r
    assert isinstance(out["listable"], list)
    assert out["listableCount"] == len(out["listable"])
