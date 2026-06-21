# SaaS Replicator on iii

Claude×KIMI マルチエージェント・オーケストレーション（元設計: `assets/original-report.md`）を、**iii のプリミティブ（Worker / Function / Trigger）上で動作するよう再設計・実装**した例です。

> ✅ **4-Phase + オーケストレーションパターン + 可観測性/予算まで実装済み（Claude単独で動作）。** `director` / `swarm-executor` ワーカーが UI分析→PRD→実装+テスト→可視化/デプロイを駆動し、各 Phase は型付き成果物（`ScreenAnalysis`/`Prd`/`Implementation`/`TestReport`/`VisualArtifact`/`Deployment`）を生成します。**Supervisor**（生成→採点→再生成）と **Debate→self-critique**（`provider-kimi` 在時のみ真の 2 モデル debate へ自動格上げ）も配線済み。プロバイダ呼び出しは `withObservability` が span トレース + トークン予算（`SAAS_TOKEN_BUDGET`）でガードします。Phase3 テストは `iii-sandbox` があれば microVM で実行（無ければ tester ロールにフォールバック）、Phase4 は `approval-gate` 検出時のみ承認を求めます。`provider::resolve` の role-binding と **stub プロバイダ**で API キー無しでも end-to-end 実行・検証でき（`npm run demo`）、`provider-anthropic` で Claude 実行、`provider-kimi` を足すと分析/可視化/テストが自動的に KIMI へ再束縛されます（ロードマップは [DESIGN.md](./DESIGN.md) §13）。

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
  director.ts       startProject / advance(4-Phase 駆動) + approval + HTTP(saas::start/status)
  swarm.ts          swarm::ui::analyze-screen / swarm::viz::render / swarm::test::run
  demo.ts           runDemo()（stub で 4-Phase 完走デモ）
  adapters/
    iiiEngine.ts    本番アダプタ（Engine → iii バス）
    memoryEngine.ts インメモリ・アダプタ（テスト用：state ストア + queue ドレイン）
  logic/
    roleBinding.ts  役割→プロバイダ解決（純粋・テスト対象）
    pipeline.ts     4-Phase 進行ロジック（純粋・テスト対象）
    artifacts.ts    成果物の型 + parseJsonFromContent + build*（純粋・テスト対象）
    prompts.ts      役割/Phase ごとの構造化プロンプト（純粋）
    review.ts       Supervisor 判定 parseCritique/accepted（純粋・テスト対象）
    budget.ts       トークン予算会計 extractUsage/addUsage/overBudget（純粋・テスト対象）
tests/
  roleBinding / pipeline / artifacts / patterns / budget .test.ts  純粋ロジック + パターンの単体テスト
  integration.test.ts                           MemoryEngine で 4-Phase を end-to-end 実行（sandbox 経由/フォールバック含む）
  demo.test.ts                                  runDemo() のスモーク（done 到達 + テレメトリ）
iii-config.yaml     エンジン設定（queue concurrency = スウォーム並列度 / iii-sandbox・llm-budget 例）
```

ハンドラは `Engine` 抽象に対してのみ書かれているため、本番は `iiiEngine`、テストは `MemoryEngine` を注入でき、**実エンジン・API キー無しで 4-Phase 全体を走らせて検証**できます。

## セットアップ & テスト（エンジン不要）

```bash
cd examples/saas-replicator
npm install
npm run typecheck                  # tsc --noEmit
npm test                          # 単体 + MemoryEngine による 4-Phase end-to-end 統合テスト（計26件）
npm run demo                      # stub で 4-Phase を done まで完走し成果物/テレメトリを出力
SAAS_TOKEN_BUDGET=1 npm run demo  # トークン予算ガード（BudgetExceededError）を確認
```

## 実行

### Claude 単独モード（既定 / 実プロバイダ）

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export SAAS_PROVIDER_MODE=live
iii --config iii-config.yaml                 # engine + 本ワーカー（iii-exec 経由）を起動
iii worker add provider-anthropic            # Claude
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
