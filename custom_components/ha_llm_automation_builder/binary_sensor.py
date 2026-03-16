"""Binary sensor platform."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ConnectionOkBinarySensor(runtime), ConnectionOkLegacyBinarySensor(runtime)])


class ConnectionOkBinarySensor(CoordinatorEntity, BinarySensorEntity):
    _attr_name = "llm_connection"
    _attr_has_entity_name = True

    def __init__(self, runtime) -> None:
        super().__init__(runtime.coordinator)

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.get("connection", {}).get("ok", False)


class ConnectionOkLegacyBinarySensor(ConnectionOkBinarySensor):
    _attr_name = "polaczenie_ok"
