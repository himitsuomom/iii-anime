# 転売自動化システム 運用SOP

## 概要

本SOPに従えば、AIに詳しくない人でも1日15分でPOD転売業務を完結できます。

- **対象者**: 本システムの日次オペレーターまたはVA（バーチャルアシスタント）
- **所要時間**: 毎日15分 / 週次30分
- **前提条件**: `.env` ファイルが設定済みであること（初回のみ管理者が設定）

---

## 毎日の作業フロー（15分）

### Step 1: 商品CSVに新商品を追加（5分）

1. `data/sample_products.csv` をテキストエディタまたはExcelで開く
2. 1行目のヘッダーを参考に、新商品を1行追加する
   - `name`: 商品名（英語推奨）
   - `category`: カテゴリ（例: `Home & Kitchen / Mugs`）
   - `design_concept`: デザインの説明（英語で簡潔に）
   - `target_audience`: ターゲット顧客層
   - `platform`: 出品先（`shopify` / `mercari` / `etsy` / `amazon`）
   - `language`: 説明文の言語（`en` / `ja`）
   - `niche_keywords`: コンマ区切りのキーワード
3. ファイルを保存する

> **注意**: 著作権が疑われるキャラクター名・商標・ロゴは `design_concept` に含めない。

### Step 2: バッチ実行（5分、ほぼ自動）

ターミナル（またはVSCode のターミナル）で以下を実行する:

```bash
cd /path/to/EC
python scripts/run_full_pipeline.py
```

- 処理中はターミナルに進捗が表示される
- 自動で以下を実行する:
  1. 著作権チェック（リスクが高い商品は自動スキップ）
  2. 商品説明・タイトル・SEOキーワードの生成
  3. 結果を `output/results_YYYYMMDD_HHMMSS.json` に保存
- 所要時間の目安: 1商品あたり約30秒

### Step 3: レポート確認（5分）

1. レポートを生成する:

   ```bash
   python scripts/generate_report.py
   ```

2. `output/report_YYYYMMDD_HHMMSS.md` が生成される
3. ファイルを開いて以下を確認する:
   - **出品成功**: 価格設定が適切かどうか目視確認
   - **著作権スキップ**: スキップ理由を確認し、デザイン修正が必要か判断
   - **エラー**: エラー内容を確認（APIキー切れ・ネットワーク問題等）
4. 問題なければ完了。要対応事項は週次作業リストに追記する。

---

## 週次作業（30分）

1. **需要分析の実行**（10分）

   ```bash
   python scripts/run_analytics.py
   ```

   - ニッチキーワードのランキングを確認
   - `recommended: true` のキーワードを次週の商品CSVに反映する

2. **著作権スキップ商品のデザイン修正依頼**（10分）
   - 週のレポートでスキップされた商品を一覧化
   - デザイナー（またはAI画像生成ツール）にリデザインを依頼
   - 修正後に `design_concept` を更新して再投入

3. **出品済み商品のパフォーマンス確認**（10分）
   - Shopify管理画面でインプレッション・売上を確認
   - 売れない商品は価格見直しまたは削除を検討

---

## トラブルシューティング

| エラーメッセージ | 原因 | 対処法 |
|-----------------|------|--------|
| `ANTHROPIC_API_KEY が未設定です` | `.env` ファイルが存在しないか未設定 | `.env.example` をコピーして `.env` を作成し、APIキーを入力する |
| `output/ に results_*.json が見つかりません` | パイプラインが未実行 | `python scripts/run_full_pipeline.py` を先に実行する |
| `JSONDecodeError` | 出力JSONが壊れている | `output/` フォルダの最新ファイルを手動で確認し、削除して再実行 |
| `著作権リスクがあるため出品をスキップ` | デザインに商標・キャラクターが含まれている | `design_concept` からキャラクター名・ブランド名を削除して再実行 |
| `ConnectionError` / `TimeoutError` | ネットワークまたはAPI障害 | インターネット接続を確認後、数分待って再実行する |
| `ShopifyRateLimitError` | Shopify APIの上限超過 | 自動で待機して再試行するが、超過が続く場合は管理者に連絡 |

---

## API上限の管理

- **Shopify**: 2リクエスト/秒（バースト最大40）— システムが自動制御済み
- **PODtomatic**: 1日最大200商品 — システムが自動上限チェック済み（超過時はエラー表示）
- **Claude API**: 月額使用量に注意。[Anthropic Console](https://console.anthropic.com/) で使用量を月次確認する

> **APIコスト目安**: 1商品あたり約0.02〜0.05ドル（著作権チェック + 説明文生成）

---

## ファイル・ディレクトリ構成（参考）

```
EC/
├── data/
│   └── sample_products.csv   # ← 毎日ここに商品を追記
├── output/
│   ├── results_*.json        # バッチ実行結果（自動生成）
│   └── report_*.md           # レポート（自動生成）
├── scripts/
│   ├── run_full_pipeline.py  # メインバッチスクリプト
│   ├── run_analytics.py      # 需要分析スクリプト
│   └── generate_report.py    # レポート生成スクリプト
└── .env                      # APIキー（コミット禁止）
```

---

## 初回セットアップ（管理者のみ）

1. `.env.example` をコピーして `.env` を作成:

   ```bash
   cp .env.example .env
   ```

2. `.env` を開き、各APIキーを入力する:
   - `ANTHROPIC_API_KEY`: [Anthropic Console](https://console.anthropic.com/) で取得
   - `SHOPIFY_STORE_URL` / `SHOPIFY_ACCESS_TOKEN`: Shopify管理画面 → アプリ → カスタムアプリ
   - `PODTOMATIC_API_KEY`: [PODtomatic](https://podtomatic.com/) のダッシュボード
   - `MERCARI_ACCESS_TOKEN`: メルカリAPI申請後に取得

3. 依存パッケージのインストール:

   ```bash
   pip install -r requirements.txt
   ```

4. 動作確認（APIキー不要のサンプル実行）:

   ```bash
   python scripts/run_analytics.py
   ```
