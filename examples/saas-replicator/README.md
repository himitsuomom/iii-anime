# SaaS Replicator on iii（設計）

Claude×KIMI マルチエージェント・オーケストレーション（元設計: `assets/original-report.md`）を、**iii のプリミティブ（Worker / Function / Trigger）上で動作するよう再設計・実装**した例です。

> ✅ **ステージ1（Claude単独で動く骨格）実装済み。** 4-Phase パイプラインを `director` / `swarm-executor` ワーカーとして実装し、`provider::resolve` による role-binding と **stub プロバイダ**で、API キー無しでも end-to-end 実行できます。`provider-anthropic` を足せば Claude 実行、`provider-kimi` を足せば分析/可視化/テストが自動的に KIMI へ再束縛されます（ロードマップは [DESIGN.md](./DESIGN.md) §13）。

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
  iii.ts            iii クライアント（registerWorker）
  log.ts            最小ロガー
  hooks.ts          useApi（HTTP トリガ登録ヘルパ）
  state.ts          state::* ラッパ
  provider.ts       provider::resolve + stub プロバイダ + callRole
  director.ts       director::plan(HTTP) / director::advance(4-Phase 駆動)
  swarm.ts          swarm::ui::analyze-screen / swarm::viz::render / swarm::test::run
  logic/
    roleBinding.ts  役割→プロバイダ解決（純粋・テスト対象）
    pipeline.ts     4-Phase 進行ロジック（純粋・テスト対象）
tests/              node:test の単体テスト（エンジン不要）
iii-config.yaml     エンジン設定（queue concurrency = スウォーム並列度）
```

## セットアップ & テスト（エンジン不要）

```bash
cd examples/saas-replicator
npm install
npm run typecheck   # tsc --noEmit
npm test            # 純粋ロジックの単体テスト（role-binding / pipeline）
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
