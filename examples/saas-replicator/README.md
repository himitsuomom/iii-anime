# SaaS Replicator on iii（設計）

Claude×KIMI マルチエージェント・オーケストレーション（元設計: `assets/original-report.md`）を、**iii のプリミティブ（Worker / Function / Trigger）上で動作するよう再設計**した例です。

> ⚠️ 現状は **設計フェーズのみ**。本ディレクトリには設計書と参照アセットのみが含まれ、実コード（`src/`, `iii-config.yaml`, `package.json`）はまだありません。

## ねらい

- **オーケストレーション基盤は iii 自身**にする（Claw Groups / MCP / A2A を iii の state / queue / 関数呼び出し / ライブ・ワーカーレジストリへ置換）。
- **Claude 単独で回る**ことを必須要件にする。`provider-anthropic` のみで Phase 1〜4 が end-to-end で成立。
- `provider-kimi` を足すと、分析・可視化・並列テストが自動的に KIMI へ再束縛される（progressive enhancement）。

## ドキュメント

- **[DESIGN.md](./DESIGN.md)** — 本体（アーキテクチャ図 / 概念マッピング / 役割マトリックス / 4-Phase ワークフロー / プロバイダ抽象 / 実行・検証手順 / リスク / ロードマップ）。
- `assets/` — 元コンセプト図 4 点と元レポート（`original-report.md`）。

## 想定する起動（実装後）

```bash
# Claude 単独モード（既定）
export ANTHROPIC_API_KEY=sk-...
iii --config iii-config.yaml
iii worker add iii-state iii-queue iii-sandbox iii-observability approval-gate provider-anthropic
curl -X POST http://localhost:3111/saas/replicate \
  -H 'Content-Type: application/json' \
  -d '{"target":"Trello","screenshots":[...],"requirements":"日本語UI/PWA/レスポンシブ"}'

# Claude×KIMI モード（任意・段階的強化）
iii worker add provider-kimi   # 足すだけで自動的に役割が再束縛される
```

詳細・前提・検証方法は [DESIGN.md](./DESIGN.md) を参照してください。
