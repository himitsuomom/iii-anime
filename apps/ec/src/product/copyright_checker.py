"""Claude APIを使ったAIデザインの著作権リスク評価。"""

import json
import re
from dataclasses import dataclass, field

import anthropic

from src.config import ANTHROPIC_API_KEY, CLAUDE_MAX_TOKENS, CLAUDE_MODEL

_SYSTEM_PROMPT = """\
あなたは知的財産権・著作権に詳しいリーガルアドバイザーです。
AIが生成したデザインの説明文を受け取り、著作権・商標リスクを評価します。

評価観点：
1. 商標・キャラクター・有名人・ロゴへの類似
2. 著名ブランドのスタイル・デザイン模倣
3. 「fan art」的な要素（版権キャラ・映画・アニメ等の暗示）
4. 色合い・形状がブランドアイデンティティと酷似

出力ルール：
- JSONのみ出力する（前後にテキスト・コードブロック不要）
- 形式: {"is_safe": bool, "risk_level": "low"|"medium"|"high", "issues": [...], "recommendation": "..."}\
"""


def _build_check_prompt(design_description: str, product_name: str) -> str:
    return f"""以下のAI生成デザインを著作権・商標の観点で評価してください。

商品名: {product_name}
デザイン説明: {design_description}

上記の内容に以下の問題がないか判断してください：
- 既存の商標・ロゴ・キャラクターとの類似
- 著名ブランドのスタイル模倣
- 有名人・映画・アニメ等を想起させる要素
- fan art 的な要素

Output ONLY valid JSON in this exact format (no markdown, no extra text):
{{"is_safe": true, "risk_level": "low", "issues": [], "recommendation": "出品可能です。"}}""".strip()


@dataclass
class CopyrightCheckResult:
    """著作権チェックの結果。"""

    is_safe: bool
    risk_level: str
    issues: list[str] = field(default_factory=list)
    recommendation: str = ""


class CopyrightChecker:
    """Claude APIを使ったAIデザインの著作権リスク評価器。"""

    def __init__(self, api_key: str = ANTHROPIC_API_KEY) -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY が未設定です。.env を確認してください。")
        self._client = anthropic.Anthropic(api_key=api_key)

    def check(self, design_description: str, product_name: str) -> CopyrightCheckResult:
        """デザイン説明文と商品名から著作権リスクを評価する。

        Args:
            design_description: AIが生成したデザインの説明文。
            product_name: 商品名。

        Returns:
            CopyrightCheckResult: 評価結果。

        Raises:
            ValueError: Claude APIのレスポンスがJSON形式でない場合。
        """
        user_prompt = _build_check_prompt(design_description, product_name)

        response = self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        block = response.content[0]
        if not isinstance(block, anthropic.types.TextBlock):
            raise ValueError(
                f"Claude APIがテキスト以外のブロックを返しました: {type(block).__name__}"
            )
        raw = block.text.strip()
        return self._parse_response(raw)

    @staticmethod
    def _parse_response(raw: str) -> CopyrightCheckResult:
        """JSONレスポンスをCopyrightCheckResultに変換。

        Args:
            raw: Claude APIからの生テキスト。

        Returns:
            CopyrightCheckResult: パース結果。

        Raises:
            ValueError: JSON形式でない場合。
        """
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Claude APIのレスポンスがJSON形式ではありません: {e}\n---\n{raw}"
            ) from e

        return CopyrightCheckResult(
            is_safe=bool(data.get("is_safe", False)),
            risk_level=str(data.get("risk_level", "high")),
            issues=list(data.get("issues", [])),
            recommendation=str(data.get("recommendation", "")),
        )
