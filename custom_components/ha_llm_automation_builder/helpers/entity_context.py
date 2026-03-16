"""Entity context helpers."""

from __future__ import annotations

from collections.abc import Iterable

ALLOWED_DOMAINS = {
    "light",
    "switch",
    "sensor",
    "binary_sensor",
    "climate",
    "cover",
    "person",
    "device_tracker",
}


def collect_entities(entity_ids: Iterable[str], domain_filter: bool = True) -> list[str]:
    entities = []
    for entity_id in entity_ids:
        domain = entity_id.split(".", 1)[0]
        if not domain_filter or domain in ALLOWED_DOMAINS:
            entities.append(entity_id)
    return sorted(set(entities))
