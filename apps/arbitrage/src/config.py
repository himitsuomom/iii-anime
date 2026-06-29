"""設定の読み込み。閾値は config/default.yaml に集約し、一部は環境変数で上書きする。

変更前にコメントを必ず読むこと（マスター指示書 §3-8: 閾値はコード直書きしない）。
`load_settings()` は YAML を読み、`ARB_DRY_RUN` / `FX_STATIC_RATE` などの env で上書きした
イミュータブルな `Settings` を返す。エンジン非依存（ユニットテスト可能）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# config/default.yaml（このファイルからの相対）。
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "default.yaml"


@dataclass(frozen=True)
class ProfitSettings:
    floor_jpy: int
    min_margin_percent: float


@dataclass(frozen=True)
class FxSettings:
    base: str
    quote: str
    buffer_percent: float
    static_rate: float


@dataclass(frozen=True)
class SourcingSettings:
    interval_seconds: int
    max_items_per_run: int


@dataclass(frozen=True)
class Settings:
    profit: ProfitSettings
    fx: FxSettings
    sourcing: SourcingSettings
    # 空運転（Dry-run）。true の間は副作用関数が実呼び出しをしない。
    dry_run: bool


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def load_settings(config_path: Path | None = None) -> Settings:
    """YAML を読み、env で上書きした Settings を返す。

    上書きされる env:
        ARB_DRY_RUN     → mode.dry_run
        FX_STATIC_RATE  → fx.static_rate
    """
    path = config_path or DEFAULT_CONFIG_PATH
    raw: dict[str, Any] = {}
    if path.exists():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            raw = loaded

    profit_raw = raw.get("profit", {}) or {}
    fx_raw = raw.get("fx", {}) or {}
    sourcing_raw = raw.get("sourcing", {}) or {}
    mode_raw = raw.get("mode", {}) or {}

    profit = ProfitSettings(
        floor_jpy=int(profit_raw.get("floor_jpy", 1500)),
        min_margin_percent=float(profit_raw.get("min_margin_percent", 20)),
    )
    fx = FxSettings(
        base=str(fx_raw.get("base", "USD")),
        quote=str(fx_raw.get("quote", "JPY")),
        buffer_percent=float(fx_raw.get("buffer_percent", 5)),
        static_rate=_env_float("FX_STATIC_RATE", float(fx_raw.get("static_rate", 150.0))),
    )
    sourcing = SourcingSettings(
        interval_seconds=int(sourcing_raw.get("interval_seconds", 3600)),
        max_items_per_run=int(sourcing_raw.get("max_items_per_run", 10)),
    )
    dry_run = _env_bool("ARB_DRY_RUN", bool(mode_raw.get("dry_run", True)))

    return Settings(profit=profit, fx=fx, sourcing=sourcing, dry_run=dry_run)
