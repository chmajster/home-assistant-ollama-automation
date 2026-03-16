"""Coordinator for LLM provider status."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import COORDINATOR_UPDATE_INTERVAL_SECONDS
from .helpers.errors import LlmAutomationError


class LlmStatusCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, adapter: Any, model: str) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name="LLM Automation Builder status",
            update_interval=timedelta(seconds=COORDINATOR_UPDATE_INTERVAL_SECONDS),
        )
        self._adapter = adapter
        self._model = model

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            conn = await self._adapter.test_connection()
            model = await self._adapter.test_model(self._model)
        except LlmAutomationError as err:
            raise UpdateFailed(str(err)) from err
        return {"connection": conn, "model": model}
