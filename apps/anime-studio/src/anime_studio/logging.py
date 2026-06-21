"""Lightweight structured logger.

Uses the iii-observability ``Logger`` when available (so worker runs feed OTEL),
and falls back to ``print`` for the standalone CLI / tests where no engine is
attached.
"""

from __future__ import annotations

import json
from typing import Any, Protocol


class Logger(Protocol):
    def info(self, message: str, meta: dict[str, Any] | None = ...) -> None: ...
    def error(self, message: str, meta: dict[str, Any] | None = ...) -> None: ...


class ConsoleLogger:
    """Minimal stdout logger matching the iii Logger surface used here."""

    def __init__(self, name: str = "anime-studio") -> None:
        self._name = name

    def _emit(self, level: str, message: str, meta: dict[str, Any] | None) -> None:
        suffix = f" {json.dumps(meta, ensure_ascii=False)}" if meta else ""
        print(f"[{self._name}] {level.upper()} {message}{suffix}")

    def info(self, message: str, meta: dict[str, Any] | None = None) -> None:
        self._emit("info", message, meta)

    def error(self, message: str, meta: dict[str, Any] | None = None) -> None:
        self._emit("error", message, meta)


def default_logger(name: str = "anime-studio") -> Logger:
    return ConsoleLogger(name)
