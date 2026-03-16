"""Home Assistant integration entrypoint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .const import DOMAIN, PLATFORMS, PROVIDER_OLLAMA

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


@dataclass(slots=True)
class IntegrationRuntime:
    config: dict[str, Any]
    adapter: object
    coordinator: Any
    history_store: Any
    last_result: dict[str, Any]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from homeassistant.const import Platform
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .coordinator import LlmStatusCoordinator
    from .llm.ollama import OllamaAdapter
    from .llm.openai_compatible import OpenAICompatibleAdapter
    from .services import async_register_services
    from .storage import HistoryStore

    session = async_get_clientsession(hass)
    conf = dict(entry.options) if entry.options else dict(entry.data)
    if conf["provider"] == PROVIDER_OLLAMA:
        adapter = OllamaAdapter(session, conf["base_url"], conf.get("api_key"))
    else:
        adapter = OpenAICompatibleAdapter(session, conf["base_url"], conf.get("api_key"))

    coordinator = LlmStatusCoordinator(hass, adapter, conf["model"])
    await coordinator.async_config_entry_first_refresh()

    runtime = IntegrationRuntime(conf, adapter, coordinator, HistoryStore(hass), {})
    hass.data[DOMAIN][entry.entry_id] = runtime

    await async_register_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR, Platform.BINARY_SENSOR])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .services import async_unregister_services

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            await async_unregister_services(hass)
    return unloaded
