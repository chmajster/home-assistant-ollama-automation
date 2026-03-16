"""Sensor platform."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            LastYamlSensor(runtime),
            LastYamlLegacySensor(runtime),
            LlmStatusSensor(runtime),
            LlmStatusLegacySensor(runtime),
            SelectedModelSensor(runtime),
            SelectedModelLegacySensor(runtime),
        ]
    )


class BaseRuntimeSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, runtime) -> None:
        super().__init__(runtime.coordinator)
        self.runtime = runtime


class LastYamlSensor(BaseRuntimeSensor):
    _attr_name = "llm_last_yaml"

    @property
    def native_value(self) -> str:
        return self.runtime.last_result.get("yaml", "")[:255]


class LlmStatusSensor(BaseRuntimeSensor):
    _attr_name = "llm_status"

    @property
    def native_value(self) -> str:
        return "ok" if self.coordinator.data.get("connection", {}).get("ok") else "error"


class SelectedModelSensor(BaseRuntimeSensor):
    _attr_name = "llm_model"

    @property
    def native_value(self) -> str:
        return self.runtime.config["model"]


class LastYamlLegacySensor(LastYamlSensor):
    _attr_name = "ostatni_wygenerowany_yaml"


class LlmStatusLegacySensor(LlmStatusSensor):
    _attr_name = "status_llm"


class SelectedModelLegacySensor(SelectedModelSensor):
    _attr_name = "wybrany_model"
