"""Diagnostics support."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.diagnostics import async_redact_data

from .const import CONF_API_KEY, DOMAIN

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    runtime = hass.data[DOMAIN][entry.entry_id]
    data = {
        "entry": dict(entry.data),
        "status": runtime.coordinator.data,
        "last_result": runtime.last_result,
    }
    return async_redact_data(data, TO_REDACT)
