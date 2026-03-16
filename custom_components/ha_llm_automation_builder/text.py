"""Text platform for chat-like prompt input."""

from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AutomationPromptText(runtime, entry.entry_id)])


class AutomationPromptText(TextEntity):
    _attr_name = "automation_prompt"
    _attr_has_entity_name = True
    _attr_native_max = 4000
    _attr_native_min = 0
    _attr_pattern = ".*"

    def __init__(self, runtime, entry_id: str) -> None:
        self.runtime = runtime
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_automation_prompt"

    @property
    def native_value(self) -> str:
        return self.runtime.ui_prompt

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=self.runtime.config.get("name", "LLM Automation Builder"),
            manufacturer="Custom",
            model="LLM Automation Builder",
        )

    async def async_set_value(self, value: str) -> None:
        self.runtime.ui_prompt = value
        self.async_write_ha_state()
