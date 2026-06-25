"""EC を iii ワーカー化するアダプタ層（Phase 2）。

設計書の関数コントラクト（products::describe / copyright::check /
analytics::* / pipeline::run）を EC の実モジュールに束ねる薄い層。
エンジン非依存の純粋部品（serializers / offline / services / handlers）と、
エンジン接続を行う app に分かれている。
"""
