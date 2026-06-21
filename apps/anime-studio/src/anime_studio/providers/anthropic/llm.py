"""Anthropic-backed LLM adapter.

The one 'real-ish' provider. It transparently degrades to an injected mock when
the ``anthropic`` package is missing, no API key is configured, or any
network/runtime error occurs — so the pipeline always completes regardless of
environment. The model id is supplied by config (never hardcoded here).
"""

from __future__ import annotations

from typing import Any

from ..mock.llm import MockLLMProvider
from ..types import LLMMessage, LLMResponse


class AnthropicLLMProvider:
    name = "anthropic"

    def __init__(self, model: str, api_key: str | None, fallback: MockLLMProvider | None = None) -> None:
        self._model = model
        self._fallback = fallback or MockLLMProvider()
        self._client: Any | None = None
        if api_key:
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic(api_key=api_key)
            except Exception:  # pragma: no cover - import/availability guard
                self._client = None

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> LLMResponse:
        if self._client is None:
            return await self._fallback.complete(
                messages, system=system, max_tokens=max_tokens, temperature=temperature
            )
        try:
            kwargs: dict[str, Any] = {
                "model": self._model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
            }
            if system:
                kwargs["system"] = system
            resp = await self._client.messages.create(**kwargs)
            text = "".join(getattr(block, "text", "") for block in resp.content)
            usage = getattr(resp, "usage", None)
            return LLMResponse(
                text=text,
                model=self._model,
                mocked=False,
                usage={"input_tokens": getattr(usage, "input_tokens", None),
                       "output_tokens": getattr(usage, "output_tokens", None)} if usage else None,
            )
        except Exception:  # network / rate limit / API change -> never break the pipeline
            return await self._fallback.complete(
                messages, system=system, max_tokens=max_tokens, temperature=temperature
            )
