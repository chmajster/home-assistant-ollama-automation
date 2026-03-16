from custom_components.ha_llm_automation_builder.const import PROVIDER_OLLAMA, PROVIDER_OPENAI_COMPATIBLE
from custom_components.ha_llm_automation_builder.helpers.provider_runtime import (
    build_provider_adapter,
    normalize_base_url,
    resolve_provider_base_url,
)
from custom_components.ha_llm_automation_builder.llm.ollama import OllamaAdapter
from custom_components.ha_llm_automation_builder.llm.openai_compatible import OpenAICompatibleAdapter


def test_normalize_base_url_adds_http_scheme():
    assert normalize_base_url("192.168.1.50:11434") == "http://192.168.1.50:11434"


def test_resolve_provider_base_url_from_ollama_host_and_port():
    result = resolve_provider_base_url(
        provider=PROVIDER_OLLAMA,
        base_url=None,
        ollama_host="192.168.1.50",
        ollama_port=11434,
    )
    assert result == "http://192.168.1.50:11434"


def test_resolve_provider_base_url_from_ollama_host_url_adds_port():
    result = resolve_provider_base_url(
        provider=PROVIDER_OLLAMA,
        base_url=None,
        ollama_host="http://192.168.1.50",
        ollama_port=11434,
    )
    assert result == "http://192.168.1.50:11434"


def test_resolve_provider_base_url_keeps_explicit_openai_url():
    result = resolve_provider_base_url(
        provider=PROVIDER_OPENAI_COMPATIBLE,
        base_url="https://api.example.com/v1",
        ollama_host="192.168.1.50",
        ollama_port=11434,
    )
    assert result == "https://api.example.com/v1"


def test_build_provider_adapter_selects_ollama():
    adapter = build_provider_adapter(None, PROVIDER_OLLAMA, "http://127.0.0.1:11434")  # type: ignore[arg-type]
    assert isinstance(adapter, OllamaAdapter)


def test_build_provider_adapter_selects_openai_compatible():
    adapter = build_provider_adapter(None, PROVIDER_OPENAI_COMPATIBLE, "https://api.example.com/v1")  # type: ignore[arg-type]
    assert isinstance(adapter, OpenAICompatibleAdapter)
    assert adapter._base_url == "https://api.example.com"
