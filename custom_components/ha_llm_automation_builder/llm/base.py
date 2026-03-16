"""Base LLM provider adapter interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class GenerationRequest:
    prompt: str
    system_prompt: str
    model: str
    temperature: float
    top_p: float
    max_tokens: int
    timeout: int


@dataclass(slots=True)
class GenerationResponse:
    text: str
    raw: dict[str, Any]


class BaseLlmAdapter:
    """Base provider adapter."""

    async def list_models(self) -> list[str]:
        raise NotImplementedError

    async def test_connection(self) -> dict[str, Any]:
        raise NotImplementedError

    async def test_model(self, model: str) -> dict[str, Any]:
        raise NotImplementedError

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        raise NotImplementedError
