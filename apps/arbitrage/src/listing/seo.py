"""eBay 出品向けの簡易 SEO（M5）。純関数。

タイトルにキーワードを織り込み（80字上限）、検索タグを生成する。海外向け文章は
機械翻訳のまま投稿せず用語の自然さを担保する方針だが、Phase 0/3 では下書きの素材生成に留める
（実投稿は人間 or 後フェーズの自動投稿）。
"""

from __future__ import annotations

EBAY_TITLE_MAX = 80


def build_seo_title(base_title: str, keywords: list[str]) -> str:
    """ベースタイトルにキーワードを付与し、80字に収める。"""
    title = base_title.strip()
    for kw in keywords:
        kw = kw.strip()
        if not kw or kw.lower() in title.lower():
            continue
        candidate = f"{title} {kw}".strip()
        if len(candidate) > EBAY_TITLE_MAX:
            break
        title = candidate
    return title[:EBAY_TITLE_MAX]


def build_tags(keywords: list[str], *, limit: int = 12) -> list[str]:
    """重複除去・空白除去したタグ列（最大 limit 個）。"""
    seen: set[str] = set()
    tags: list[str] = []
    for kw in keywords:
        norm = kw.strip()
        key = norm.lower()
        if norm and key not in seen:
            seen.add(key)
            tags.append(norm)
        if len(tags) >= limit:
            break
    return tags
