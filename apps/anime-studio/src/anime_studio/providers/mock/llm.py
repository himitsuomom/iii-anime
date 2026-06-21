"""Deterministic mock LLM.

Returns a stable, prompt-derived response so the whole pipeline runs (and tests
assert exact output) without any network or API key. The text is a concise
echo-style synthesis of the prompt's intent, good enough to populate the
production bible's creative fields in dry-run mode.
"""

from __future__ import annotations

import hashlib

from ..types import LLMMessage, LLMResponse

_ADJECTIVES = ["bright", "tender", "playful", "surprising", "warm", "bold", "gentle", "vivid"]


class MockLLMProvider:
    name = "mock"

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> LLMResponse:
        prompt = "\n".join(m.content for m in messages)
        digest = hashlib.sha256(((system or "") + prompt).encode("utf-8")).hexdigest()
        adjective = _ADJECTIVES[int(digest[:2], 16) % len(_ADJECTIVES)]
        # Deterministic, short, content-bearing line keyed to the request.
        text = f"[{adjective}] {_first_line(prompt)} (mock-{digest[:8]})"
        return LLMResponse(text=text, model="mock", mocked=True)


def _first_line(prompt: str) -> str:
    for line in prompt.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:160]
    return "untitled"
