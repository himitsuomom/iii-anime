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
| ✨ 商品説明ジェネレーター | 商品情報からSEO最適化済みの説明文・タイトル・キーワードを生成 | Claude |
| 💬 問い合わせアシスタント | 顧客の質問にストリーミングで自動応答 | Claude |
| ✅ 4Dタスクボード | Doing/Deciding/Delegating/Designing でタスクを棚卸し（localStorage保存） | — |

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

- `ANTHROPIC_API_KEY` 未設定時、AI機能は HTTP 503 を返し、UIにエラーを表示します
  （アプリ自体は起動・操作可能）。
- 実行環境のネットワークポリシーが `api.anthropic.com` への egress を許可している必要があります。

## スコープ外（MVP）

実決済・実在庫連携・外部EC API（Amazon/楽天/Shopify）連携、認証、永続DBは未実装です。
