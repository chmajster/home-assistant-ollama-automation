"""Ollama provider adapter."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientSession

from .base import BaseLlmAdapter, GenerationRequest, GenerationResponse
from ..helpers.errors import ModelUnavailableError, ProviderConnectionError


class OllamaAdapter(BaseLlmAdapter):
    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        api_key: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def list_models(self) -> list[str]:
        try:
            async with self._session.get(
                f"{self._base_url}/api/tags",
                headers=self._headers,
                timeout=self._timeout,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except (ClientError, TimeoutError) as err:
            raise ProviderConnectionError(str(err)) from err
        return [item["name"] for item in data.get("models", []) if "name" in item]

    async def test_connection(self) -> dict[str, Any]:
        models = await self.list_models()
        return {"ok": True, "models_count": len(models)}

    async def test_model(self, model: str) -> dict[str, Any]:
        models = await self.list_models()
        if model not in models:
            raise ModelUnavailableError(f"Model {model} not found")
        return {"ok": True, "model": model}

    async def pull_model(self, model: str) -> dict[str, Any]:
        payload = {"name": model, "stream": False}
        try:
            async with self._session.post(
                f"{self._base_url}/api/pull",
                json=payload,
                headers=self._headers,
                timeout=self._timeout,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except (ClientError, TimeoutError) as err:
            raise ProviderConnectionError(str(err)) from err
        return {"ok": True, "model": model, "response": data}

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "system": request.system_prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "top_p": request.top_p,
                "num_predict": request.max_tokens,
            },
        }
        try:
            async with self._session.post(
                f"{self._base_url}/api/generate",
                json=payload,
                headers=self._headers,
                timeout=request.timeout,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except (ClientError, TimeoutError) as err:
            raise ProviderConnectionError(str(err)) from err
        return GenerationResponse(text=data.get("response", ""), raw=data)
