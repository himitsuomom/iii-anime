"""Shared provider value types."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: Literal["user", "assistant"] = "user"
    content: str


class LLMResponse(BaseModel):
    text: str
    model: str = ""
    mocked: bool = False
    usage: dict[str, Any] | None = None


class GenSpec(BaseModel):
    kind: Literal["image", "video", "bgm", "se"]
    prompt: str
    negative_prompt: str | None = None
    # Optional reference image (e.g. a character ref used as an init image for
    # image-to-video) and a target file path for the downloaded asset.
    init_image: str | None = None
    out_path: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
