"""iii 関数ハンドラ本体。

各ハンドラは `(data: dict, services: Services) -> dict` の純粋な形に保ち、
エンジン/ネットワークに依存しない。`app.py` がこれらを `register_function` に束ねる。
dict 境界なのでオフラインで直接ユニットテストできる。
"""

from typing import Any

from src.analytics.price_tracker import DemandSignal
from src.io.product_loader import load_from_csv, load_from_json
from src.worker.serializers import (
    copyright_result_to_dict,
    niche_score_to_dict,
    pipeline_result_to_dict,
    product_input_from_dict,
    product_input_to_dict,
    product_listing_from_dict,
    product_listing_to_dict,
)
from src.worker.services import Services


def handle_describe(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`products::describe` — 商品入力から説明文リスティングを生成する。"""
    inp = product_input_from_dict(data)
    listing = services.generator.generate(inp)
    return product_listing_to_dict(listing)


def handle_products_load(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`products::load` — CSV/JSON ファイルまたはインライン rows を ProductInput[] に読み込む。

    payload:
      - `{"source": "csv"|"json", "path": "..."}` … ファイルから読み込む
      - `{"rows": [{name, category, ...}, ...]}` … インライン dict を変換する
    """
    rows = data.get("rows")
    if rows is not None:
        products = [product_input_from_dict(row) for row in rows]
    else:
        source = str(data.get("source", "")).lower()
        path = data.get("path")
        if not path:
            raise ValueError("path（または rows）が必要です。")
        if source == "csv":
            products = load_from_csv(str(path))
        elif source == "json":
            products = load_from_json(str(path))
        else:
            raise ValueError("source は 'csv' または 'json' を指定してください。")

    return {
        "products": [product_input_to_dict(p) for p in products],
        "count": len(products),
    }


def handle_copyright_check(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`copyright::check` — デザイン説明と商品名から著作権リスクを評価する。"""
    design = str(data.get("design_concept") or data.get("design_description") or "")
    name = str(data.get("name") or data.get("product_name") or "")
    if not design or not name:
        raise ValueError("name と design_concept（または design_description）が必要です。")
    result = services.checker.check(design_description=design, product_name=name)
    return copyright_result_to_dict(result)


def handle_analytics_price(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`analytics::price` — 原価・利益率・競合価格から推奨価格を算出する。"""
    if "cost" not in data:
        raise ValueError("cost が必要です。")
    cost = float(data["cost"])
    target_margin = float(data.get("target_margin", 0.3))
    competitor_prices = [float(p) for p in (data.get("competitor_prices") or [])]
    suggested = services.price_tracker.suggest_price_with_competition(
        cost=cost,
        target_margin=target_margin,
        competitor_prices=competitor_prices,
    )
    return {
        "suggested_price": suggested,
        "cost": cost,
        "target_margin": target_margin,
        "competitor_count": len(competitor_prices),
    }


def handle_analytics_demand(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`analytics::demand` — キーワード群を需要スコアでランク付けする。

    payload に `signals` を含めると（`{keyword, search_volume_estimate,
    trend_score, platform}` の配列）、その場で需要シグナルを登録してから分析する。
    """
    keywords = [str(k) for k in (data.get("keywords") or [])]
    if not keywords:
        raise ValueError("keywords（配列）が必要です。")

    for raw in data.get("signals") or []:
        services.price_tracker.record_demand_signal(
            DemandSignal(
                keyword=str(raw["keyword"]),
                search_volume_estimate=int(raw.get("search_volume_estimate", 0)),
                trend_score=float(raw.get("trend_score", 0.0)),
                platform=str(raw.get("platform", "")),
            )
        )

    ranked = services.demand_analyzer.rank_keywords(keywords)
    return {
        "scores": [niche_score_to_dict(s) for s in ranked],
        "recommended": [niche_score_to_dict(s) for s in ranked if s.recommended],
    }


async def handle_pipeline_run(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`pipeline::run` — 著作権チェック→説明生成→（任意で）出品の一連を実行する。"""
    inp = product_input_from_dict(data)
    result = await services.pipeline.run(inp)
    return pipeline_result_to_dict(result)


async def handle_list_shopify(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`listing::shopify` — ProductListing を Shopify に出品する。"""
    if services.shopify_client is None:
        raise ValueError("Shopify クレデンシャル未設定です（SHOPIFY_STORE_URL / SHOPIFY_ACCESS_TOKEN）。")
    listing = product_listing_from_dict(data.get("listing") or data)
    return await services.shopify_client.create_product(listing)


async def handle_list_mercari(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`listing::mercari` — ProductListing をメルカリに出品する。"""
    if services.mercari_client is None:
        raise ValueError("メルカリ クレデンシャル未設定です（MERCARI_ACCESS_TOKEN）。")
    listing = product_listing_from_dict(data.get("listing") or data)
    price = int(data.get("price", 1000))
    return await services.mercari_client.create_product(listing, price)


async def handle_list_podtomatic(data: dict[str, Any], services: Services) -> dict[str, Any]:
    """`listing::podtomatic` — ProductListing を PODtomatic にアップロードする。"""
    if services.podtomatic_client is None:
        raise ValueError("PODtomatic クレデンシャル未設定です（PODTOMATIC_API_KEY）。")
    listing = product_listing_from_dict(data.get("listing") or data)
    return await services.podtomatic_client.upload_product(listing)
