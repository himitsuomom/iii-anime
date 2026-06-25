"""プロジェクト全体の定数・設定。変更前にコメントを必ず読むこと。"""

import os

# === Claude API ===
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
# claude-sonnet-4-6 はコスト・速度・品質のバランスが最良
CLAUDE_MODEL: str = "claude-sonnet-4-6"
CLAUDE_MAX_TOKENS: int = 2048

# === Shopify API ===
# レート制限: 2リクエスト/秒（バースト最大40）を厳守
SHOPIFY_STORE_URL: str = os.environ.get("SHOPIFY_STORE_URL", "")
SHOPIFY_ACCESS_TOKEN: str = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
SHOPIFY_API_VERSION: str = "2024-01"
SHOPIFY_RATE_LIMIT_PER_SEC: float = 2.0
SHOPIFY_BURST_LIMIT: int = 40

# === PODtomatic API ===
# 1日最大200商品アップロード制限あり。超過するとアカウント停止リスク
PODTOMATIC_API_KEY: str = os.environ.get("PODTOMATIC_API_KEY", "")
PODTOMATIC_DAILY_UPLOAD_LIMIT: int = 200

# === プラットフォーム別文字数制限 ===
PLATFORM_LIMITS: dict[str, dict[str, int]] = {
    "shopify": {
        "title_max": 255,
        "description_max": 60000,
        "tags_max_count": 250,
        "tag_max_chars": 255,
    },
    "mercari": {
        "title_max": 40,
        "description_max": 1000,
        "tags_max_count": 0,
        "tag_max_chars": 0,
    },
    "etsy": {
        "title_max": 140,
        "description_max": 65535,
        "tags_max_count": 13,
        "tag_max_chars": 20,
    },
    "amazon": {
        "title_max": 200,
        "description_max": 2000,
        "bullet_points_max": 5,
        "bullet_point_max_chars": 500,
        "keywords_max_chars": 250,
    },
}

# === メルカリ API ===
# タイトル最大40文字・説明最大1000文字制限あり
MERCARI_ACCESS_TOKEN: str = os.environ.get("MERCARI_ACCESS_TOKEN", "")

# === デフォルト設定 ===
DEFAULT_PLATFORM: str = os.environ.get("TARGET_PLATFORM", "shopify")
DEFAULT_LANGUAGE: str = "en"
