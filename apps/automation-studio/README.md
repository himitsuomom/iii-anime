# Automation Studio

EC・転売事業者向けの **AI業務自動化ツール**。アップロードされたレポート
『「週4時間」働く × 自分がいなくても回る仕組み』の中心テーマ（AI×EC自動化）を
実装した、独立したサンプルアプリです。

> 注: このアプリは iii（orchestration プラットフォーム）本体とは独立しており、
> `apps/automation-studio/` 配下で完結します。

## 機能

| 機能 | 説明 | AI |
|---|---|---|
| 📊 ダッシュボード | 売上・自動応答率・作業時間などのKPIスコアカード | — |
| ✨ 商品説明ジェネレーター | 商品情報からSEO最適化済みの説明文・タイトル・キーワードを生成 | Claude（無い場合はテンプレート） |
| 💬 問い合わせアシスタント | 顧客の質問にストリーミングで自動応答 | Claude（無い場合は定型FAQ） |
| 🧮 利益計算機 | 仕入・販売価格・各種手数料・送料から、利益率・損益分岐を即試算 | — |
| 📈 ROIシミュレーター | 事業フェーズと作業時間から推奨ツール・コスト・削減効果を概算 | — |
| 🗺️ 実践ロードマップ | 「週4時間」体制への5ステップ＋成功5原則（進捗をlocalStorage保存） | — |
| ✅ 4Dタスクボード | Doing/Deciding/Delegating/Designing でタスクを棚卸し（localStorage保存） | — |

利益計算機・ROIシミュレーター・ロードマップ・タスクボードは、AIレポート
`ai_ecommerce_business_report.md`（§4.3/§6.3/§8.1/§11）から実装した、**API不要で完結する**機能です。

## APIなしでも動作（オフラインモード）

`ANTHROPIC_API_KEY` が未設定でも、アプリは**そのまま実用的に動作**します。

- 商品説明ジェネレーター → ルールベースのテンプレートで説明文を生成（結果に「テンプレート生成」バッジ）
- 問い合わせアシスタント → キーワードFAQで定型回答をストリーミング
- その他の機能（計算・ロードマップ等）→ もともとAI不要

キーを設定すると、上記2機能が自動的に Claude（`claude-opus-4-8`）に切り替わります
（サイドバーの「オフラインモード」表示が消えます）。

## アーキテクチャ

- **フロントエンド**: React 19 + Vite + Tailwind CSS v4
- **バックエンド**: Hono（`@hono/node-server`）。`ANTHROPIC_API_KEY` をサーバ側で保持し、
  `@anthropic-ai/sdk` 経由で **`claude-opus-4-8`** を呼び出す
  - `POST /api/generate-description` — structured outputs（json_schema）で構造化生成
  - `POST /api/chat` — SSE ストリーミング応答
  - `GET /api/health` — APIキー設定状況

APIキーはブラウザに渡さず、必ずサーバ経由で呼び出します。

## セットアップ

```bash
# リポジトリルートで依存をインストール
pnpm install

cd apps/automation-studio
cp .env.example .env
# .env を編集して ANTHROPIC_API_KEY=... を設定

# フロント(5173) + API(8787) を同時起動
pnpm dev
```

ブラウザで http://localhost:5173 を開く。

### その他のコマンド

```bash
pnpm build       # 型チェック + 本番ビルド (dist/)
pnpm start       # ビルド済み dist/ を Hono で配信 (本番)
pnpm type-check  # フロント + サーバの型チェック
pnpm lint        # Biome
```

## 注意

- `ANTHROPIC_API_KEY` 未設定でもアプリは動作します（AI機能はテンプレート/定型FAQで代替）。
- Claude を利用する場合は、実行環境のネットワークポリシーが `api.anthropic.com` への
  egress を許可している必要があります。

## スコープ外（MVP）

実決済・実在庫連携・外部EC API（Amazon/楽天/Shopify）連携、認証、永続DBは未実装です。
