"""SDLC 10フェーズの定義と参照ヘルパー。

各フェーズは `PhaseSpec` で表現する。`get_phase(n)` で 1..10 のフェーズを取得し、
範囲外は `ValueError` を送出する。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhaseSpec:
    """1つの SDLC フェーズの仕様。"""

    number: int
    name_ja: str
    name_en: str
    philosophy: str
    model: str
    output_dir: str


# フェーズ番号 -> 仕様。アップロードされたスラッシュコマンド定義と整合させている。
_PHASES: dict[int, PhaseSpec] = {
    1: PhaseSpec(
        number=1,
        name_ja="構想・企画",
        name_en="Concept",
        philosophy="復唱プロンプト + メタプロンプト",
        model="claude-opus-4-7",
        output_dir="docs/sdlc/phase-1/",
    ),
    2: PhaseSpec(
        number=2,
        name_ja="要件定義",
        name_en="Requirements",
        philosophy="MoSCoW + 受け入れ基準の明文化",
        model="claude-opus-4-7",
        output_dir="docs/sdlc/phase-2/",
    ),
    3: PhaseSpec(
        number=3,
        name_ja="設計（System/DB/API）",
        name_en="Design",
        philosophy="Triangle（Context/Spec/Constraints）",
        model="claude-sonnet-4-6",
        output_dir="docs/sdlc/phase-3/",
    ),
    4: PhaseSpec(
        number=4,
        name_ja="バックエンド実装",
        name_en="Backend Implementation",
        philosophy="契約優先 + 小さな差分",
        model="claude-sonnet-4-6",
        output_dir="src/",
    ),
    5: PhaseSpec(
        number=5,
        name_ja="フロントエンド実装",
        name_en="Frontend Implementation",
        philosophy="コンポーネント分割 + 状態の局所化",
        model="claude-sonnet-4-6",
        output_dir="frontend/",
    ),
    6: PhaseSpec(
        number=6,
        name_ja="バックエンドテスト",
        name_en="Backend Test",
        philosophy="SDLC品質ゲート 6観点",
        model="claude-haiku-4-5",
        output_dir="tests/",
    ),
    7: PhaseSpec(
        number=7,
        name_ja="バックエンドデバッグ",
        name_en="Backend Debug",
        philosophy="仮説→再現→最小修正のループ",
        model="claude-haiku-4-5",
        output_dir="src/",
    ),
    8: PhaseSpec(
        number=8,
        name_ja="フロントエンドテスト",
        name_en="Frontend Test",
        philosophy="ユーザー操作起点の E2E 観点",
        model="claude-haiku-4-5",
        output_dir="frontend/__tests__/",
    ),
    9: PhaseSpec(
        number=9,
        name_ja="結合・リリース",
        name_en="Integration & Release",
        philosophy="リリースチェックリスト + ロールバック前提",
        model="claude-sonnet-4-6",
        output_dir="docs/sdlc/phase-9/",
    ),
    10: PhaseSpec(
        number=10,
        name_ja="フロントエンドデバッグ",
        name_en="Frontend Debug",
        philosophy="Phase7同型 + UI観点",
        model="claude-haiku-4-5",
        output_dir="frontend/",
    ),
}

MIN_PHASE = 1
MAX_PHASE = 10


def get_phase(number: int) -> PhaseSpec:
    """フェーズ番号から `PhaseSpec` を返す。1..10 以外は `ValueError`。"""
    spec = _PHASES.get(number)
    if spec is None:
        raise ValueError(
            f"phase は {MIN_PHASE}..{MAX_PHASE} の範囲で指定してください: {number!r}"
        )
    return spec


def all_phases() -> list[PhaseSpec]:
    """全フェーズを番号順で返す。"""
    return [_PHASES[n] for n in range(MIN_PHASE, MAX_PHASE + 1)]
