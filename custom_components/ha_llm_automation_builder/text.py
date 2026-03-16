"""Text platform for chat-like prompt input."""

from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AutomationPromptText(runtime)])


class AutomationPromptText(TextEntity):
    _attr_name = "automation_prompt"
    _attr_has_entity_name = True
    _attr_native_max = 4000
    _attr_native_min = 0
    _attr_pattern = ".*"

    def __init__(self, runtime) -> None:
        self.runtime = runtime

    @property
    def native_value(self) -> str:
        return self.runtime.ui_prompt

    async def async_set_value(self, value: str) -> None:
        self.runtime.ui_prompt = value
        self.async_write_ha_state()
