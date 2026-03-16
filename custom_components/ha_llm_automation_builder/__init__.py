"""Home Assistant integration entrypoint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .const import DOMAIN, PLATFORMS
from .helpers.provider_runtime import build_provider_adapter

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
    ui_prompt: str


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from homeassistant.const import Platform

    from .coordinator import LlmStatusCoordinator
    from .services import async_register_services
    from .storage import HistoryStore
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    session = async_get_clientsession(hass)
    conf = dict(entry.data)
    conf.update(entry.options or {})
    adapter = build_provider_adapter(
        session=session,
        provider=conf["provider"],
        base_url=conf["base_url"],
        api_key=conf.get("api_key"),
        timeout=conf.get("timeout"),
    )

    coordinator = LlmStatusCoordinator(hass, adapter, conf["model"])
    await coordinator.async_config_entry_first_refresh()

    runtime = IntegrationRuntime(conf, adapter, coordinator, HistoryStore(hass), {}, "")
    hass.data[DOMAIN][entry.entry_id] = runtime
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await async_register_services(hass)
    await hass.config_entries.async_forward_entry_setups(
        entry,
        [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON, Platform.TEXT],
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .services import async_unregister_services

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            await async_unregister_services(hass)
    return unloaded
