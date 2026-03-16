"""Persistent storage for generation history."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION


@dataclass(slots=True)
class HistoryItem:
    timestamp: str
    provider: str
    model: str
    prompt: str
    yaml: str


class HistoryStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_load(self) -> list[HistoryItem]:
        data = await self._store.async_load() or {"items": []}
        return [HistoryItem(**item) for item in data.get("items", [])]

    async def async_append(self, item: HistoryItem, max_items: int) -> list[HistoryItem]:
        items = await self.async_load()
        items.append(item)
        items = items[-max_items:]
        await self._store.async_save({"items": [asdict(i) for i in items]})
        return items


def build_history_item(provider: str, model: str, prompt: str, yaml: str) -> HistoryItem:
    return HistoryItem(
        timestamp=datetime.now(tz=UTC).isoformat(),
        provider=provider,
        model=model,
        prompt=prompt,
        yaml=yaml,
    )
