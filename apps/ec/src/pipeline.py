"""商品リサーチ → 著作権確認 → 説明文生成 → Shopify出品 の一連パイプライン。"""

from dataclasses import dataclass, field

from src.listing.shopify import ShopifyListing
from src.product.copyright_checker import CopyrightChecker, CopyrightCheckResult
from src.product.generator import ProductGenerator
from src.product.models import ProductInput, ProductListing


@dataclass
class PipelineResult:
    """パイプライン実行結果。"""

    product_input: ProductInput
    copyright_result: CopyrightCheckResult
    listing: ProductListing | None
    shopify_response: dict[str, object] | None = field(default=None)
    error: str = field(default="")
    success: bool = field(default=False)


class ResalePipeline:
    """商品リサーチ → 著作権確認 → 説明文生成 → Shopify出品 の一連フロー。"""

    def __init__(
        self,
        generator: ProductGenerator,
        checker: CopyrightChecker,
        shopify_client: ShopifyListing | None = None,
    ) -> None:
        self._generator = generator
        self._checker = checker
        self._shopify_client = shopify_client

    async def run(self, inp: ProductInput) -> PipelineResult:
        """単一商品のパイプラインを実行する。

        1. 著作権チェック（is_safe=False なら listing=None で早期リターン）
        2. 説明文生成
        3. Shopify出品（shopify_client が設定されている場合のみ）
        4. PipelineResult を返す

        Args:
            inp: 商品入力データ。

        Returns:
            PipelineResult: パイプライン実行結果。
        """
        try:
            copyright_result = self._checker.check(
                design_description=inp.design_concept,
                product_name=inp.name,
            )
        except Exception as exc:  # noqa: BLE001
            dummy_result = CopyrightCheckResult(
                is_safe=False,
                risk_level="high",
                issues=["著作権チェック中にエラーが発生しました"],
                recommendation="手動で確認してください。",
            )
            return PipelineResult(
                product_input=inp,
                copyright_result=dummy_result,
                listing=None,
                error=str(exc),
                success=False,
            )

        if not copyright_result.is_safe:
            return PipelineResult(
                product_input=inp,
                copyright_result=copyright_result,
                listing=None,
                error="著作権リスクがあるため出品をスキップしました。",
                success=False,
            )

        try:
            listing = self._generator.generate(inp)
        except Exception as exc:  # noqa: BLE001
            return PipelineResult(
                product_input=inp,
                copyright_result=copyright_result,
                listing=None,
                error=str(exc),
                success=False,
            )

        shopify_response: dict[str, object] | None = None
        if self._shopify_client is not None:
            try:
                shopify_response = await self._shopify_client.create_product(listing)
            except Exception as exc:  # noqa: BLE001
                return PipelineResult(
                    product_input=inp,
                    copyright_result=copyright_result,
                    listing=listing,
                    shopify_response=None,
                    error=str(exc),
                    success=False,
                )

        return PipelineResult(
            product_input=inp,
            copyright_result=copyright_result,
            listing=listing,
            shopify_response=shopify_response,
            error="",
            success=True,
        )

    async def run_batch(self, inputs: list[ProductInput]) -> list[PipelineResult]:
        """複数商品を順次処理する。

        Args:
            inputs: 商品入力データのリスト。

        Returns:
            list[PipelineResult]: 各商品のパイプライン実行結果リスト。
        """
        results = []
        for inp in inputs:
            result = await self.run(inp)
            results.append(result)
        return results
