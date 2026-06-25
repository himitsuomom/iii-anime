# @iii/contracts — 統合コントラクト（設計スケルトン）

EC(Python) ⇄ Automation Studio(TS) の**統合境界**。`schemas/*.json`（JSON Schema）を**唯一の正本**とし、
TypeScript 型と Python(Pydantic) モデルを**自動生成**して両言語で共有します。

> これは統合アーキテクチャ（`apps/automation-studio/docs/integration-architecture/`）の **Phase 1 雛形**です。
> 現時点では pnpm workspace には未登録（ビルドグラフに影響させないため）。Phase 1 着手時に
> `pnpm-workspace.yaml` の `packages:` に `packages/contracts` を追加し、生成を turbo/Makefile に組み込みます。

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

TypeScript（`json-schema-to-typescript`）:
```bash
npx -y json-schema-to-typescript@15 schemas/commerce.schema.json \
  --unreachableDefinitions --no-additionalProperties > generated/typescript/commerce.ts
```

Python / Pydantic v2（`datamodel-code-generator`）:
```bash
uvx datamodel-code-generator \
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
