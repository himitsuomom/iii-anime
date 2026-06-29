"""eBay 出品下書きの生成（M6）。純関数・副作用なし。

Phase 0 は常に `mode=dry_run, status=draft` を生成する（人間が後で投稿）。下書きは
仕入れ候補（SourceListing）と提示売価から組み立てる。実投稿（M7）は後フェーズで
`mode=auto && status=ready` のみを対象に行う。
"""

from __future__ import annotations

from src.domain.models import (
    ListingDraft,
    ListingMode,
    ListingStatus,
    Money,
    SourceListing,
)
from src.listing.seo import build_seo_title, build_tags


def build_listing_draft(
    *,
    source: SourceListing,
    price_usd: Money,
    created_at: str,
    mode: ListingMode = ListingMode.DRY_RUN,
    title: str | None = None,
    description: str | None = None,
    category_id: str | None = None,
    keywords: list[str] | None = None,
    shipping_note: str | None = None,
) -> ListingDraft:
    """仕入れ候補から eBay 出品下書きを組み立てる。

    title/description 未指定なら候補から簡易生成する（後フェーズで AI 生成に差し替え可能）。
    keywords を与えると SEO タイトル・タグを生成する（M5）。
    """
    kws = keywords or []
    base_title = title or source.title
    draft_title = build_seo_title(base_title, kws) if kws else base_title
    draft_description = description or (
        f"{source.title}\n\nCondition: {source.condition or 'see photos'}.\n"
        "Ships from Japan. Carefully packed."
    )
    if shipping_note:
        draft_description = f"{draft_description}\n\n{shipping_note}"
    return ListingDraft(
        draft_id=f"draft-{source.id}",
        source_listing_id=source.id,
        title=draft_title,
        price=price_usd,
        mode=mode,
        status=ListingStatus.DRAFT,
        created_at=created_at,
        description=draft_description,
        category_id=category_id,
        condition=source.condition,
        image_urls=list(source.image_urls),
        tags=build_tags(kws),
        seo_keywords=list(kws),
    )
