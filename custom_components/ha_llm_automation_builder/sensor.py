"""Sensor platform."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
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
            LastYamlSensor(runtime, entry.entry_id),
            LastYamlLegacySensor(runtime, entry.entry_id),
            LlmStatusSensor(runtime, entry.entry_id),
            LlmStatusLegacySensor(runtime, entry.entry_id),
            SelectedModelSensor(runtime, entry.entry_id),
            SelectedModelLegacySensor(runtime, entry.entry_id),
        ]
    )


class BaseRuntimeSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, runtime, entry_id: str, unique_suffix: str) -> None:
        super().__init__(runtime.coordinator)
        self.runtime = runtime
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_{unique_suffix}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=self.runtime.config.get("name", "LLM Automation Builder"),
            manufacturer="Custom",
            model="LLM Automation Builder",
        )


class LastYamlSensor(BaseRuntimeSensor):
    _attr_name = "llm_last_yaml"

    def __init__(self, runtime, entry_id: str) -> None:
        super().__init__(runtime, entry_id, "llm_last_yaml")

    @property
    def native_value(self) -> str:
        return self.runtime.last_result.get("yaml", "")[:255]


class LlmStatusSensor(BaseRuntimeSensor):
    _attr_name = "llm_status"

    def __init__(self, runtime, entry_id: str) -> None:
        super().__init__(runtime, entry_id, "llm_status")

    @property
    def native_value(self) -> str:
        data = self.coordinator.data or {}
        return "ok" if data.get("connection", {}).get("ok") else "error"


class SelectedModelSensor(BaseRuntimeSensor):
    _attr_name = "llm_model"

    def __init__(self, runtime, entry_id: str) -> None:
        super().__init__(runtime, entry_id, "llm_model")

    @property
    def native_value(self) -> str:
        return self.runtime.config["model"]


class LastYamlLegacySensor(LastYamlSensor):
    _attr_name = "ostatni_wygenerowany_yaml"

    def __init__(self, runtime, entry_id: str) -> None:
        super().__init__(runtime, entry_id)
        self._attr_unique_id = f"{entry_id}_ostatni_wygenerowany_yaml"


class LlmStatusLegacySensor(LlmStatusSensor):
    _attr_name = "status_llm"

    def __init__(self, runtime, entry_id: str) -> None:
        super().__init__(runtime, entry_id)
        self._attr_unique_id = f"{entry_id}_status_llm"


class SelectedModelLegacySensor(SelectedModelSensor):
    _attr_name = "wybrany_model"

    def __init__(self, runtime, entry_id: str) -> None:
        super().__init__(runtime, entry_id)
        self._attr_unique_id = f"{entry_id}_wybrany_model"
