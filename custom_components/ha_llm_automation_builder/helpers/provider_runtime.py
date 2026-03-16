"""Helpers for provider runtime configuration and adapter construction."""

from __future__ import annotations

from urllib.parse import urlparse

from aiohttp import ClientSession

from ..const import DEFAULT_OLLAMA_PORT, PROVIDER_OLLAMA
from ..llm.ollama import OllamaAdapter
from ..llm.openai_compatible import OpenAICompatibleAdapter


def normalize_base_url(base_url: str) -> str:
    """Normalize URL and ensure scheme + host are present."""
    cleaned = (base_url or "").strip().rstrip("/")
    if not cleaned:
        raise ValueError("Base URL cannot be empty")
    if "://" not in cleaned:
        cleaned = f"http://{cleaned}"
    parsed = urlparse(cleaned)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid base URL: {base_url}")
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def resolve_provider_base_url(
    provider: str,
    base_url: str | None,
    ollama_host: str | None = None,
    ollama_port: int | None = None,
) -> str:
    """Resolve provider base URL from explicit URL or Ollama host/ip + port."""
    if provider == PROVIDER_OLLAMA and ollama_host:
        host_value = ollama_host.strip().rstrip("/")
        if not host_value:
            raise ValueError("Ollama host cannot be empty")
        if "://" in host_value:
            parsed = urlparse(host_value)
            if not parsed.netloc:
                raise ValueError(f"Invalid Ollama host value: {ollama_host}")
            netloc = parsed.netloc
            if parsed.port is None:
                resolved_port = ollama_port or DEFAULT_OLLAMA_PORT
                hostname = parsed.hostname or ""
                if ":" in hostname and not hostname.startswith("["):
                    hostname = f"[{hostname}]"
                netloc = f"{hostname}:{resolved_port}"
            host_base = f"{parsed.scheme}://{netloc}"
            return normalize_base_url(host_base)
        resolved_port = ollama_port or DEFAULT_OLLAMA_PORT
        return normalize_base_url(f"http://{host_value}:{resolved_port}")

    return normalize_base_url(base_url or "")


def build_provider_adapter(
    session: ClientSession,
    provider: str,
    base_url: str,
    api_key: str | None = None,
    timeout: int | None = None,
):
    """Create provider adapter by provider type."""
    if provider == PROVIDER_OLLAMA:
        return OllamaAdapter(session, base_url, api_key, timeout=timeout)
    return OpenAICompatibleAdapter(session, base_url, api_key, timeout=timeout)
