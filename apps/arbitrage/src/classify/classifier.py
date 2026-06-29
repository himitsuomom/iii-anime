"""商品分類（M4）。純関数・副作用なし。

仕入れ価格（円）で価格帯（小/中/大）を決める。出品比率 小5:中3:大2 の土台となる軸。
カテゴリ・プラットフォーム（仕入れ元）も合わせて分類のキーにする。
"""

from __future__ import annotations

from src.config import ClassifySettings

# 価格帯ラベル（小/中/大）。
BAND_SMALL = "small"
BAND_MEDIUM = "medium"
BAND_LARGE = "large"


def price_band(amount_jpy: int, cfg: ClassifySettings) -> str:
    """仕入れ価格（円）から価格帯を返す。"""
    if amount_jpy <= cfg.small_max_jpy:
        return BAND_SMALL
    if amount_jpy <= cfg.medium_max_jpy:
        return BAND_MEDIUM
    return BAND_LARGE
