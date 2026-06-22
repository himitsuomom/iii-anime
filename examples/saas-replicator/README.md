# SaaS Replicator on iii

Claude×KIMI マルチエージェント・オーケストレーション（元設計: `assets/original-report.md`）を、**iii のプリミティブ（Worker / Function / Trigger）上で動作するよう再設計・実装**した例です。

> ✅ **4-Phase + パターン + 可観測性/予算 + 実コード生成/実行 + 深掘り（UI集約/本格アプリ/デプロイ）まで実装済み（Claude単独で動作）。** `director` / `swarm-executor` が UI分析→PRD→**PRD駆動の実アプリ生成+実行テスト**→可視化/デプロイを駆動します。**Phase1** は複数画面を**コンポーネントカタログ + デザインシステム**に集約（`aggregateScreens`）。**Phase3** は **PRD から実マルチファイルアプリ（models + api + app + test）を生成**（`synthesizeApp`）し、生成テストを実走（`iii-sandbox` があれば microVM、無ければ子プロセス）。**Phase4** は **deploy worker（deploy/vercel/netlify）があれば実公開・無ければシミュレート**（`deploy`）。**Supervisor** と **Debate→self-critique**（`provider-kimi` 在時のみ真の 2 モデル debate）、`withObservability` の span トレース + トークン予算（`SAAS_TOKEN_BUDGET`）も配線済み。stub で API キー無しでも end-to-end 実行・検証でき（`npm run demo` — 生成アプリが実走）、`provider-kimi` を足すと分析/可視化/テストが自動的に KIMI へ再束縛されます。live 起動前は `saas::preflight` が設定を検証します（ロードマップは [DESIGN.md](./DESIGN.md) §13）。

## ねらい

- **オーケストレーション基盤は iii 自身**にする（Claw Groups / MCP / A2A を iii の state / queue / 関数呼び出し / ライブ・ワーカーレジストリへ置換）。
- **Claude 単独で回る**ことを必須要件にする。`provider-anthropic` のみで Phase 1〜4 が end-to-end で成立。
- `provider-kimi` を足すと、分析・可視化・並列テストが自動的に KIMI へ再束縛される（progressive enhancement）。

## ドキュメント

- **[DESIGN.md](./DESIGN.md)** — 設計本体（アーキテクチャ図 / 概念マッピング / 役割マトリックス / 4-Phase ワークフロー / プロバイダ抽象 / リスク / ロードマップ）。
- `assets/` — 元コンセプト図 4 点と元レポート（`original-report.md`）。

## 構成

```
src/
  engine.ts         Engine 抽象（register/call/enqueue/listWorkers）
  orchestrator.ts   registerOrchestrator(engine)
  index.ts          本番ブート（iii アダプタ + 登録）
  log.ts            最小ロガー
  sandbox.ts        runInSandbox / sandboxAvailable（iii-sandbox 連携）
  provider.ts       registerProvider + provider::resolve + stub + callRole/callRoleJson
  patterns.ts       supervisedGenerate / debateOrCritique（Supervisor・Debate 配線）
  observability.ts  withObservability（span トレース + トークン予算ガード）
  workspace.ts      createWorkspace / materialize / cleanup（生成コードの書き出し）
  executor.ts       sandbox/local の CodeExecutor + pickExecutor（生成テストの実行）
  deploy.ts         deploy()（deploy worker 連携 or シミュレート）
  preflight.ts      runPreflight / saas::preflight（起動前の設定検証）
  director.ts       startProject / advance(4-Phase 駆動) + approval + HTTP(saas::start/status)
  swarm.ts          swarm::ui::analyze-screen / swarm::viz::render / swarm::test::run
  demo.ts           runDemo()（stub で 4-Phase 完走デモ・生成コード実走）
  adapters/
    iiiEngine.ts    本番アダプタ（Engine → iii バス）
    memoryEngine.ts インメモリ・アダプタ（テスト用：state ストア + queue ドレイン）
  logic/
    roleBinding.ts  役割→プロバイダ解決（純粋・テスト対象）
    pipeline.ts     4-Phase 進行ロジック（純粋・テスト対象）
    artifacts.ts    成果物の型 + parseJsonFromContent + build* + buildCodebase（純粋・テスト対象）
    prompts.ts      役割/Phase ごとの構造化プロンプト（純粋）
    review.ts       Supervisor 判定 parseCritique/accepted（純粋・テスト対象）
    budget.ts       トークン予算会計 extractUsage/addUsage/overBudget（純粋・テスト対象）
    preflight.ts    buildPreflightReport（設定検証の判定）（純粋・テスト対象）
    uiAggregate.ts  aggregateScreens（複数画面→カタログ/デザインシステム）（純粋・テスト対象）
    appgen.ts       synthesizeApp（PRD→マルチファイル実アプリ）（純粋・テスト対象）
    deploy.ts       buildDeployPlan（ビルド/デプロイ計画）（純粋・テスト対象）
tests/
  roleBinding / pipeline / artifacts / patterns / budget / preflight / workspace / executor / uiAggregate / appgen / deploy  単体テスト
  integration.test.ts                           MemoryEngine で 4-Phase を end-to-end 実行（生成アプリ実走/sandbox/デプロイ）
  demo.test.ts                                  runDemo() のスモーク（done + 生成アプリ実走 + テレメトリ）
iii-config.yaml     エンジン設定（queue concurrency = スウォーム並列度 / iii-sandbox・llm-budget 例）
```

ハンドラは `Engine` 抽象に対してのみ書かれているため、本番は `iiiEngine`、テストは `MemoryEngine` を注入でき、**実エンジン・API キー無しで 4-Phase 全体を走らせて検証**できます。

## セットアップ & テスト（エンジン不要）

```bash
cd examples/saas-replicator
npm install
npm run typecheck                  # tsc --noEmit
npm test                          # 単体 + 4-Phase end-to-end 統合（生成アプリを実走、計46件）
npm run demo                      # stub で 4-Phase を done まで完走し成果物/生成ファイル/テレメトリを出力
SAAS_TOKEN_BUDGET=1 npm run demo  # トークン予算ガード（BudgetExceededError）を確認
```

## 実行

### Claude 単独モード（既定 / 実プロバイダ）

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export SAAS_PROVIDER_MODE=live
iii --config iii-config.yaml                 # engine + 本ワーカー（iii-exec 経由）を起動
iii worker add provider-anthropic            # Claude
# 起動時に preflight が自動実行され、必須ワーカー/ANTHROPIC_API_KEY の有無をログ検証します
curl -X POST http://localhost:3111/saas/replicate \
  -H 'Content-Type: application/json' \
  -d '{"target":"Trello","requirements":"日本語UI/PWA/レスポンシブ","screenshots":[{"id":"board"},{"id":"card"}]}'
curl http://localhost:3111/saas/status/<projectId>
```

### スタブモード（API キー不要・配線確認用）

```bash
export SAAS_PROVIDER_MODE=stub
iii --config iii-config.yaml
curl -X POST http://localhost:3111/saas/replicate -H 'Content-Type: application/json' \
  -d '{"target":"Trello","screenshots":[{"id":"board"}]}'
```

### Claude×KIMI モード（任意・段階的強化）

```bash
iii worker add provider-kimi   # 足すだけで analyzer/visualizer/tester/swarm が自動的に KIMI へ再束縛される
```

詳細・前提は [DESIGN.md](./DESIGN.md) を参照してください。
