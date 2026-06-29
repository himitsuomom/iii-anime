"""API キー無しでも稼働するためのオフライン代替実装。

automation-studio の `server/lib/offline.ts` と同じ思想で、ANTHROPIC_API_KEY が
未設定の環境でもワーカーが説明文生成・著作権チェックを返せるようにする。
出力品質は Claude には及ばないが、決定論的で外部依存ゼロなので CI / ローカル /
オフライン運用で安全に動く。本物の `ProductGenerator` / `CopyrightChecker` と
同じメソッドシグネチャを持つ（duck typing で差し替え可能）。
"""

from src.config import PLATFORM_LIMITS
from src.product.copyright_checker import CopyrightCheckResult
from src.product.models import Language, ProductInput, ProductListing

# 著作権・商標リスクを想起させる代表的な語（簡易ヒューリスティック）。
# 本番の判定は Claude に任せ、ここはキー無し時の安全側フォールバック。
_RISKY_TERMS: tuple[str, ...] = (
    "disney",
    "pokemon",
    "ポケモン",
    "nintendo",
    "任天堂",
    "marvel",
    "ghibli",
    "ジブリ",
    "gucci",
    "nike",
    "supreme",
    "fan art",
    "ファンアート",
    "character",
    "キャラクター",
    "logo",
    "ロゴ",
    "brand",
    "ブランド",
)


def _clip(text: str, max_chars: int) -> str:
    """max_chars に収まるよう末尾を切り詰める（0 以下なら無制限扱い）。"""
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


class OfflineProductGenerator:
    """ルールベースの説明文ジェネレーター（ProductGenerator 互換）。"""

    def generate(self, inp: ProductInput) -> ProductListing:
        """商品情報から決定論的にリスティングを組み立てる。"""
        limits = PLATFORM_LIMITS.get(inp.platform.value, PLATFORM_LIMITS["shopify"])
        is_ja = inp.language == Language.JA

        title = _clip(f"{inp.name} | {inp.category}", limits.get("title_max", 255))

        if is_ja:
            description = (
                f"{inp.target_audience}に向けた{inp.category}。{inp.design_concept}。"
                "丁寧に仕上げた一点で、日常から特別な日まで活躍します。"
            )
            bullets = [
                f"コンセプト: {inp.design_concept}",
                f"対象: {inp.target_audience}にぴったり",
                f"カテゴリー: {inp.category}",
                "高品質な素材と仕上げ",
                "ギフトにも最適",
            ]
        else:
            description = (
                f"{inp.category} crafted for {inp.target_audience}. {inp.design_concept}. "
                "A thoughtfully made piece for everyday use and special moments alike."
            )
            bullets = [
                f"Concept: {inp.design_concept}",
                f"Made for: {inp.target_audience}",
                f"Category: {inp.category}",
                "Premium materials and finish",
                "Great as a gift",
            ]

        bullet_count = limits.get("bullet_points_max", 5)
        bullets = bullets[:bullet_count] if bullet_count > 0 else bullets

        # タグ: 商品名の語 + ニッチキーワード + カテゴリー（重複排除・上限考慮）
        raw_tags = inp.name.replace("/", " ").split() + inp.niche_keywords + [inp.category]
        tag_chars = limits.get("tag_max_chars", 20)
        seen: set[str] = set()
        tags: list[str] = []
        for tag in raw_tags:
            normalized = _clip(tag.strip(), tag_chars) if tag_chars > 0 else tag.strip()
            key = normalized.lower()
            if normalized and key not in seen:
                seen.add(key)
                tags.append(normalized)
        tag_count = limits.get("tags_max_count", 13)
        tags = tags[:tag_count] if tag_count > 0 else []

        seo_keywords = list(
            dict.fromkeys(inp.niche_keywords + [inp.category, inp.target_audience])
        )[:8]

        return ProductListing(
            title=title,
            description=_clip(description, limits.get("description_max", 60000)),
            bullet_points=bullets,
            tags=tags,
            seo_keywords=seo_keywords,
            platform=inp.platform,
            language=inp.language,
        )


class OfflineCopyrightChecker:
    """ルールベースの著作権チェッカー（CopyrightChecker 互換）。"""

    def check(self, design_description: str, product_name: str) -> CopyrightCheckResult:
        """既知のリスク語を走査して保守的に判定する。"""
        haystack = f"{product_name}\n{design_description}".lower()
        hits = [term for term in _RISKY_TERMS if term.lower() in haystack]

        if hits:
            return CopyrightCheckResult(
                is_safe=False,
                risk_level="high",
                issues=[f"潜在的な商標・著作権リスク語を検出: {', '.join(sorted(set(hits)))}"],
                recommendation="該当表現を削除し、オリジナルなデザイン記述に修正してください。",
            )

        return CopyrightCheckResult(
            is_safe=True,
            risk_level="low",
            issues=[],
            recommendation="（オフライン簡易判定）明らかなリスク語は検出されませんでした。最終確認は人手で行ってください。",
        )
