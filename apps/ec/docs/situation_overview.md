# 状況整理（2026-06-15時点）

## プロジェクト現状

| 項目 | 状況 |
|------|------|
| ブランチ | `claude/resale-project-overview-couxo9` |
| フェーズ | 調査完了 → 基盤構築中 |
| ビジネスモデル | **POD自動化転売**（決定） |

---

## 調査資料のサマリー

### 1. AI eコマース戦略PDF（Qwen生成・全13ページ）

- **AIドロップシッピング**: AutoDS・Spocket・Dropship.io等で商品調達〜出品〜CSを完全自動化
- **AI転売モデル**: Sniffie（動的価格設定）・TradeGecko（需要予測）・MonkeyLearn（レビュー分析）
- **地域別比較**:
  - 中国：eコマースのDNA（大規模データ×迅速製造）
  - 北米：民主化ツール（Shopify×AI アプリ）
  - 東南アジア：Shopee・Lazada主導の競争力強化

### 2. AIビジネス完全ガイド（ビジネスレポート）

- POD自動化：月$50〜150の投資で月$800〜5,000の収益見込み
- TikTok Shop事例：28日間で$2.4M（2,000クリエイター連携）
- 80/20ルール：完全自動化を目指さない
- スタートアップロードマップ：Week1（基盤）→ Month1-3（拡張）→ Month3-6（スケール）

### 3. SQLite DB（`utmc_store.sqlite`）

- **正体**: Alibaba/Taobao系アプリのUTMCトラッキングSDKのローカルキャッシュ
- `ali_trackid`・`adid`・`ucm`等Alibaba固有パラメータを確認
- **売上・商品データなし**。インフラ監視用（AppMonitor）
- 現段階での活用価値：なし（参考情報）

### 4. LLM Wiki PDF（Claude Codeの使い方）

| 技術 | プロジェクト適用 |
|------|---------------|
| Output Shape指定 | 商品説明プロンプトを形式・制約まで明示（`prompts/`） |
| XMLタグ構造化 | `<role><task><constraints><output_format>` で精度+20% |
| 15分ウォーターフォール | Spec→Plan→Execute→Review で機能追加 |
| Self-Refine | 生成→レビュー→修正の3ステップ |
| CLAUDE.md | 60行以内（本ファイル：現在約40行） |
| Extended Thinking | 価格最適化・需要予測に `ultrathink` を使う |

---

## 転売ビジネスモデル比較（決定済み）

| モデル | 月収 | 自動化 | リスク | 決定 |
|-------|------|--------|-------|------|
| POD自動化 | $800〜5K | **最高** | 著作権のみ | ✅ **採用** |
| オンラインアービトラージ | $1K〜10K | 中〜高 | 在庫リスク | 将来検討 |
| ドメイン転売 | $500〜5K | 高 | 流動性 | 将来検討 |
| 小口転売 | $300〜3K | 中 | 価格変動 | 将来検討 |

---

## 次のマイルストーン

- [x] CLAUDE.md 作成（完了）
- [x] ディレクトリ構造作成（完了）
- [x] プロンプトテンプレート作成（完了）
- [ ] Week 1: `src/product/` に商品説明生成スクリプト実装
- [ ] Week 2-4: `src/listing/` に Shopify 出品スクリプト実装
- [ ] Month 2: `src/analytics/` に価格・需要分析実装
- [ ] Month 3+: PODtomatic 連携でフルオート化
