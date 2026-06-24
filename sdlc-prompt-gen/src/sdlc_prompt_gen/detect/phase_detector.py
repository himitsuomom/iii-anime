"""自由文から SDLC フェーズをキーワードベースで推定する。

設計方針:
- 各フェーズに代表キーワードを割り当て、入力文に含まれる「異なるキーワードの数」で
  スコアリングする（出現回数ではなく種類数）。
- 最高スコアのフェーズを採用する。スコア 0（どれにも当たらない / 空文字）なら
  フェーズ 0・確信度 0.0 を返す。
- 確信度は当たったキーワード種類数に比例（`0.45 * score` を 1.0 で頭打ち）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# フェーズ番号 -> キーワード集合（すべて小文字で保持し、入力も小文字化して照合）。
_KEYWORDS: dict[int, tuple[str, ...]] = {
    1: ("企画", "構想", "コンセプト", "アイデア", "やりたい", "作りたい", "ビジョン"),
    2: ("要件", "要求", "ユーザーストーリー", "受け入れ基準", "スコープ", "機能一覧"),
    3: ("設計", "アーキ", "データベース", "db", "api設計", "スキーマ", "er図", "テーブル"),
    4: ("実装", "バックエンド", "エンドポイント", "サーバー", "ビジネスロジック"),
    5: ("フロント", "ui実装", "画面実装", "コンポーネント", "画面を"),
    6: ("テスト", "テストコード", "カバレッジ", "ユニットテスト", "単体テスト", "pytest"),
    7: ("デバッグ", "バグ", "不具合", "例外", "スタックトレース", "落ちる"),
    8: ("e2e", "uiテスト", "画面テスト", "スナップショット", "playwright"),
    9: ("リリース", "デプロイ", "本番", "運用", "ロールバック", "ci/cd"),
    10: ("表示崩れ", "レイアウト", "css", "スタイル", "レンダリング", "描画"),
}


@dataclass(frozen=True)
class DetectResult:
    """フェーズ検出結果。"""

    phase: int
    confidence: float
    matched: list[str] = field(default_factory=list)


def _score(text_lower: str, keywords: tuple[str, ...]) -> list[str]:
    return [kw for kw in keywords if kw in text_lower]


def detect_phase(text: str) -> DetectResult:
    """入力文から最も近い SDLC フェーズを推定する。

    どのキーワードにも当たらない場合・空文字の場合は phase=0, confidence=0.0。
    """
    if not text or not text.strip():
        return DetectResult(phase=0, confidence=0.0, matched=[])

    text_lower = text.lower()

    best_phase = 0
    best_matched: list[str] = []
    for phase in sorted(_KEYWORDS):  # タイは小さいフェーズ番号を優先
        matched = _score(text_lower, _KEYWORDS[phase])
        if len(matched) > len(best_matched):
            best_phase = phase
            best_matched = matched

    if not best_matched:
        return DetectResult(phase=0, confidence=0.0, matched=[])

    confidence = min(1.0, round(0.45 * len(best_matched), 2))
    return DetectResult(phase=best_phase, confidence=confidence, matched=best_matched)
