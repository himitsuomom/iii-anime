"""為替レートプロバイダ（M3）。

既定は config の静的レート（オフライン・決定的）。`FX_LIVE=1` のときだけ無料の
為替 API（キー不要の exchangerate.host）から実レートを取得し、失敗時は静的レートへ退避する。
いずれの場合も `FxRate` にバッファを適用して返す（利益計算は悲観側の実効レートを使う）。
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any, Protocol

from src.config import FxSettings
from src.domain.models import FxRate
from src.fx.calculator import build_fx_rate


class HttpClientLike(Protocol):
    """httpx.get 互換の最小インターフェース（テストで差し替え可能）。"""

    def get(self, url: str, *, params: dict[str, Any], timeout: float) -> Any: ...


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class FxProvider:
    """設定の静的レート、または（FX_LIVE 時）無料 API の実レートを返す。"""

    def __init__(
        self,
        settings: FxSettings,
        *,
        live: bool | None = None,
        http_client: HttpClientLike | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.settings = settings
        self.live = (os.environ.get("FX_LIVE", "").strip() == "1") if live is None else live
        self._http = http_client
        self.timeout = timeout

    def _fetch_live_rate(self, base: str, quote: str) -> float | None:
        """無料 API から base→quote の実レートを取る。失敗なら None。"""
        client = self._http
        if client is None:
            import httpx

            client = httpx  # module exposes get()
        try:
            resp = client.get(
                "https://api.exchangerate.host/latest",
                params={"base": base, "symbols": quote},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            rate = data.get("rates", {}).get(quote)
            return float(rate) if rate is not None else None
        except Exception:  # noqa: BLE001 — ネットワーク失敗は静的レートへ退避
            return None

    def get_rate(self, base: str | None = None, quote: str | None = None) -> FxRate:
        """バッファ適用済み FxRate を返す。live 失敗時は静的レートへ退避する。"""
        b = base or self.settings.base
        q = quote or self.settings.quote
        rate = self.settings.static_rate
        source = "static-config"
        if self.live:
            live_rate = self._fetch_live_rate(b, q)
            if live_rate is not None:
                rate = live_rate
                source = "exchangerate.host"
        return build_fx_rate(
            base=b,
            quote=q,
            rate=rate,
            buffer_percent=self.settings.buffer_percent,
            as_of=_now_iso(),
            source=source,
        )
