"""Binary sensor platform."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ConnectionOkBinarySensor(runtime, entry.entry_id),
            ConnectionOkLegacyBinarySensor(runtime, entry.entry_id),
        ]
    )


class ConnectionOkBinarySensor(CoordinatorEntity, BinarySensorEntity):
    _attr_name = "llm_connection"
    _attr_has_entity_name = True

    def __init__(self, runtime, entry_id: str) -> None:
        super().__init__(runtime.coordinator)
        self.runtime = runtime
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_llm_connection"

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data or {}
        return data.get("connection", {}).get("ok", False)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=self.runtime.config.get("name", "LLM Automation Builder"),
            manufacturer="Custom",
            model="LLM Automation Builder",
        )


class ConnectionOkLegacyBinarySensor(ConnectionOkBinarySensor):
    _attr_name = "polaczenie_ok"

    def __init__(self, runtime, entry_id: str) -> None:
        super().__init__(runtime, entry_id)
        self._attr_unique_id = f"{entry_id}_polaczenie_ok"
