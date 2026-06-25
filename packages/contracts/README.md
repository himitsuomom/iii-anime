# @iii/contracts — 統合コントラクト（Phase 1）

EC(Python) ⇄ Automation Studio(TS) の**統合境界**。`schemas/*.json`（JSON Schema）を**唯一の正本**とし、
TypeScript 型と Python(Pydantic) モデルを**自動生成**して両言語で共有します。

> **Phase 1 確定済み**: スキーマを**実装済みの iii 関数 I/O**に合わせて確定しました
> （`ProductInput` / `ProductListing` / `CopyrightCheckResult` / `NicheScore`（apps/ec 由来・snake_case）、
> `DescribeRequest` / `GeneratedDescription`（ai::describe-product・camelCase）等）。
> 生成は `make contracts-codegen` で再現できます（下記）。
>
> なお `ProductListing`(EC, snake_case) と `GeneratedDescription`(AS, camelCase) は**別形**で、
> `apps/ec/src/worker/remote.py` の `RemoteProductGenerator` が両者を写像します。
>
> pnpm workspace への登録（生成物を両 app が直接 import）は Phase 5 のパッケージング統一に合わせて行う予定
> （現時点では生成物を artifact として保持し、ビルドグラフに影響させない）。

## 構成

```
packages/contracts/
├─ schemas/
│  └─ commerce.schema.json        # 正本（Product/Order/Inventory/Inquiry/Pricing/GeneratedDescription ...）
└─ generated/                     # 生成物（手で編集しない）
   ├─ typescript/commerce.ts      # → apps/automation-studio が import
   └─ python/commerce.py          # → apps/ec が import
```

## 生成コマンド（検証済み）

リポジトリルートから一括再生成:
```bash
make contracts-codegen
```

個別に実行する場合（`packages/contracts/` から）:
```bash
# TypeScript（json-schema-to-typescript）
npx -y json-schema-to-typescript@15 schemas/commerce.schema.json \
  --unreachableDefinitions --no-additionalProperties > generated/typescript/commerce.ts

# Python / Pydantic v2（datamodel-code-generator）
uvx --from datamodel-code-generator datamodel-codegen \
  --input schemas/commerce.schema.json --input-file-type jsonschema \
  --output generated/python/commerce.py
```

いずれも本リポジトリで実行・検証済み（生成された TS は `tsc --strict` で型チェック通過）。

## 規約
- **追加的変更を基本**にメジャー固定（`$id: .../commerce/v1`）。破壊的変更は新バージョン（`/v2`）＋新ネームスペース関数。
- 金額は `Money`（最小単位 integer + ISO4217）で float ドリフトを回避。
- フィールド名は両言語で同一（生成時に変換しない）。

## 関連
- 設計書: `apps/automation-studio/docs/integration-architecture/README.md`
- インタラクティブ版: 同ディレクトリの `index.html`
