"""最小 Telegram 通知（M9）。

Dry-run または認証情報未設定なら**ネットワークに触れず**プレビューだけ返す
（`{"ok": True, "dryRun": True, "preview": ...}`）。本送信は token+chat_id があり
dry_run=False のときのみ Telegram Bot API を叩く。EC の services 的な認証ゲートに倣う。
"""

from __future__ import annotations

import os
from typing import Any

import httpx


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


class TelegramNotifier:
    """Telegram への通知。dry-run / 未設定時はプレビューのみ。"""

    def __init__(
        self,
        *,
        token: str | None = None,
        chat_id: str | None = None,
        dry_run: bool = True,
        timeout: float = 10.0,
    ) -> None:
        self.token = token if token is not None else _env("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id if chat_id is not None else _env("TELEGRAM_CHAT_ID")
        self.dry_run = dry_run
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, text: str, source_url: str | None = None) -> dict[str, Any]:
        """メッセージを送る（または dry-run プレビューを返す）。

        売れた商品の通知では仕入れ元 URL を含めて人間が即購入できるようにする。
        """
        body = text if not source_url else f"{text}\n\n仕入れ元: {source_url}"

        # 空運転 or 未設定 → 実送信しない。
        if self.dry_run or not self.configured:
            return {"ok": True, "dryRun": True, "preview": body}

        resp = httpx.post(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            json={"chat_id": self.chat_id, "text": body},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return {"ok": True, "dryRun": False, "result": resp.json()}
