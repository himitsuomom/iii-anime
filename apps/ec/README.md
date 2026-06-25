# EC 転売自動化プロジェクト

AI（Claude Code）を活用したPOD転売の自動化システム。

## ビジネスモデル

**POD（Print on Demand）自動化転売**

| 指標 | 目標値 |
|------|--------|
| 初期投資 | $200〜500 |
| 月額ツール費 | $50〜150 |
| 月収見込み | $800〜5,000 |
| 自動化率 | 80%（PODtomatic + Claude API） |

### なぜPOD自動化か
- 在庫リスクゼロ（受注後に製造・発送）
- 最高レベルの自動化（1日最大200商品をAIが自動出品）
- 小規模スタート可能（$200から始められる）

## プロジェクト構造

```
src/
├── product/    # 商品リサーチ・説明文生成
├── listing/    # 出品自動化スクリプト
└── analytics/  # 価格・需要分析

prompts/        # LLMプロンプトテンプレート
docs/           # ドキュメント・状況整理
```

## セットアップ

```bash
# 依存パッケージのインストール（実装後に更新）
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .env に API キーを入力

# テスト実行
python -m pytest src/
```

## 成功の5原則（調査より）

1. **80/20ルール** — 80%をAIに任せ、20%を人間が仕上げる
2. **仕組み先行** — 収益モデル設計 → コンテンツ量産
3. **1点集中** — まずPOD1業務でAI成功体験を作る
4. **データ駆動PDCA** — KPIを数値で測り改善を回す
5. **ツール2本縛り** — Claude Code + Canva AI のみで深掘り

## ロードマップ

- [ ] Week 1: Claude API で商品説明自動生成（`src/product/`）
- [ ] Week 2-4: Shopify 出品スクリプト（`src/listing/`）
- [ ] Month 2: 価格分析・需要予測（`src/analytics/`）
- [ ] Month 3+: PODtomatic 連携でフルオート化
