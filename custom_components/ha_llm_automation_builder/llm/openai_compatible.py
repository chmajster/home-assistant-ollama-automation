"""OpenAI-compatible provider adapter."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientSession

from .base import BaseLlmAdapter, GenerationRequest, GenerationResponse
from ..helpers.errors import ModelUnavailableError, ProviderConnectionError


class OpenAICompatibleAdapter(BaseLlmAdapter):
    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        api_key: str | None,
        timeout: int | None = None,
    ) -> None:
        self._session = session
        normalized = base_url.rstrip("/")
        self._base_url = normalized[:-3] if normalized.endswith("/v1") else normalized
        self._api_key = api_key
        self._timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def list_models(self) -> list[str]:
        try:
            async with self._session.get(
                f"{self._base_url}/v1/models",
                headers=self._headers,
                timeout=self._timeout,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except (ClientError, TimeoutError) as err:
            raise ProviderConnectionError(str(err)) from err
        return [item["id"] for item in data.get("data", []) if "id" in item]

    async def test_connection(self) -> dict[str, Any]:
        models = await self.list_models()
        return {"ok": True, "models_count": len(models)}

    async def test_model(self, model: str) -> dict[str, Any]:
        models = await self.list_models()
        if model not in models:
            raise ModelUnavailableError(f"Model {model} not found")
        return {"ok": True, "model": model}

    async def pull_model(self, model: str) -> dict[str, Any]:
        raise ProviderConnectionError("Model pull is not supported by openai_compatible provider")

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.prompt},
            ],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "max_tokens": request.max_tokens,
        }
        try:
            async with self._session.post(
                f"{self._base_url}/v1/chat/completions",
                headers=self._headers,
                json=payload,
                timeout=request.timeout,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except (ClientError, TimeoutError) as err:
            raise ProviderConnectionError(str(err)) from err
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return GenerationResponse(text=text, raw=data)
