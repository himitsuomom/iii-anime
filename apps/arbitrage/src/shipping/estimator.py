"""国際送料の概算（M5）。純関数・副作用なし。

送料は利益を最も壊す要因（§9-2）。**容積重量と実重量の大きい方**で課金重量を出し、
複数キャリア（日本郵便）を比較して最安を選ぶ。

NOTE: 料金表は簡易な近似（base + per_g）。実運用では日本郵便の公式料金表（仕向地ゾーン別）に
差し替えること。ここで提供するのは「容積/実重量の大きい方で課金」「複数キャリア比較」のロジック。
"""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.models import Money

# 容積重量の除数（cm^3 → kg）。国際輸送の標準値。
VOLUMETRIC_DIVISOR_CM3_PER_KG = 5000


@dataclass(frozen=True)
class CarrierRate:
    carrier: str
    service: str
    max_weight_g: int
    base_jpy: int
    per_g_jpy: float


# 簡易料金表（近似）。max を超えるサービスは対象外。
CARRIER_RATES: list[CarrierRate] = [
    CarrierRate("japan_post", "small_packet_air", 2000, 800, 1.2),
    CarrierRate("japan_post", "epacket", 2000, 1000, 1.5),
    CarrierRate("japan_post", "ems", 30000, 1400, 2.0),
]


def volumetric_weight_g(length_cm: float, width_cm: float, height_cm: float) -> int:
    """容積重量（g）。寸法が無ければ 0。"""
    if length_cm <= 0 or width_cm <= 0 or height_cm <= 0:
        return 0
    kg = (length_cm * width_cm * height_cm) / VOLUMETRIC_DIVISOR_CM3_PER_KG
    return round(kg * 1000)


def chargeable_weight_g(
    actual_g: int, length_cm: float = 0, width_cm: float = 0, height_cm: float = 0
) -> int:
    """課金重量（g）＝実重量と容積重量の大きい方。"""
    return max(int(actual_g), volumetric_weight_g(length_cm, width_cm, height_cm))


@dataclass(frozen=True)
class ShippingOption:
    carrier: str
    service: str
    cost: Money
    eligible: bool


def estimate(
    actual_g: int,
    length_cm: float = 0,
    width_cm: float = 0,
    height_cm: float = 0,
) -> dict[str, object]:
    """課金重量と各キャリアの送料、最安オプションを返す（円）。"""
    chargeable = chargeable_weight_g(actual_g, length_cm, width_cm, height_cm)

    options: list[ShippingOption] = []
    for r in CARRIER_RATES:
        eligible = chargeable <= r.max_weight_g
        cost = round(r.base_jpy + r.per_g_jpy * chargeable)
        options.append(
            ShippingOption(
                carrier=r.carrier,
                service=r.service,
                cost=Money(amount=cost, currency="JPY"),
                eligible=eligible,
            )
        )

    eligible_opts = [o for o in options if o.eligible]
    cheapest = min(eligible_opts, key=lambda o: o.cost.amount) if eligible_opts else None

    return {
        "chargeableWeightG": chargeable,
        "options": [
            {
                "carrier": o.carrier,
                "service": o.service,
                "cost": {"amount": o.cost.amount, "currency": o.cost.currency},
                "eligible": o.eligible,
            }
            for o in options
        ],
        "cheapest": (
            {
                "carrier": cheapest.carrier,
                "service": cheapest.service,
                "cost": {"amount": cheapest.cost.amount, "currency": cheapest.cost.currency},
            }
            if cheapest is not None
            else None
        ),
    }
