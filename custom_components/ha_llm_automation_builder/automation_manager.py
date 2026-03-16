"""Helpers for creating and modifying Home Assistant automations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify


@dataclass(slots=True)
class AutomationOperationResult:
    ok: bool
    mode: str
    automation_id: str | None
    alias: str | None
    entity_id: str | None
    warnings: list[str]
    error: str | None = None


def _coerce_automation_object(raw: Any) -> dict[str, Any]:
    if isinstance(raw, list):
        if len(raw) != 1 or not isinstance(raw[0], dict):
            raise ValueError("Expected a single automation object.")
        raw = raw[0]
    if not isinstance(raw, dict):
        raise ValueError("Automation YAML must parse to an object.")
    return dict(raw)


def _ensure_unique_id(base_id: str, existing_ids: set[str]) -> str:
    if base_id not in existing_ids:
        return base_id
    idx = 2
    while f"{base_id}_{idx}" in existing_ids:
        idx += 1
    return f"{base_id}_{idx}"


def _load_automations_sync(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []
    parsed = yaml.safe_load(content)
    if parsed is None:
        return []
    if not isinstance(parsed, list):
        raise ValueError("automations.yaml must contain a list.")
    items: list[dict[str, Any]] = []
    for item in parsed:
        if isinstance(item, dict):
            items.append(dict(item))
    return items


def _save_automations_sync(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dumped = yaml.safe_dump(items, allow_unicode=True, sort_keys=False)
    path.write_text(dumped, encoding="utf-8")


def _automation_to_yaml_text(automation: dict[str, Any]) -> str:
    return yaml.safe_dump(automation, allow_unicode=True, sort_keys=False).strip()


def _find_automation_index(items: list[dict[str, Any]], identifier: str) -> int | None:
    lookup = identifier.strip().lower()
    for idx, item in enumerate(items):
        auto_id = str(item.get("id", "")).lower()
        alias = str(item.get("alias", "")).lower()
        entity_id = f"automation.{auto_id}" if auto_id else ""
        if lookup in {auto_id, alias, entity_id.lower()}:
            return idx
    return None


async def async_list_automations(hass: HomeAssistant) -> list[dict[str, Any]]:
    path = Path(hass.config.path("automations.yaml"))
    items = await hass.async_add_executor_job(_load_automations_sync, path)
    output: list[dict[str, Any]] = []
    for item in items:
        automation_id = str(item.get("id") or "")
        alias = str(item.get("alias") or "")
        output.append(
            {
                "id": automation_id,
                "alias": alias,
                "entity_id": f"automation.{automation_id}" if automation_id else None,
                "yaml": _automation_to_yaml_text(item),
                "initial_state": item.get("initial_state"),
            }
        )
    return output


async def async_get_automation(hass: HomeAssistant, identifier: str) -> dict[str, Any] | None:
    items = await async_list_automations(hass)
    lookup = identifier.strip().lower()
    for item in items:
        if lookup in {
            (item.get("id") or "").lower(),
            (item.get("alias") or "").lower(),
            (item.get("entity_id") or "").lower(),
        }:
            return item
    return None


def _prepare_automation(
    raw_yaml: str,
    existing_items: list[dict[str, Any]],
    enabled: bool | None,
    mode: str,
    target_identifier: str | None,
) -> tuple[dict[str, Any], int | None, list[str]]:
    warnings: list[str] = []
    parsed = yaml.safe_load(raw_yaml)
    automation = _coerce_automation_object(parsed)

    existing_ids = {str(item.get("id")) for item in existing_items if item.get("id")}
    alias = str(automation.get("alias") or "").strip()
    if not alias:
        warnings.append("Alias missing; generated alias was applied.")
        alias = "LLM Automation"
        automation["alias"] = alias

    if enabled is not None:
        automation["initial_state"] = bool(enabled)

    target_idx: int | None = None
    if target_identifier:
        target_idx = _find_automation_index(existing_items, target_identifier)
        if target_idx is None:
            raise ValueError(f"Target automation not found: {target_identifier}")

    if mode == "overwrite":
        if target_idx is None:
            if alias:
                target_idx = _find_automation_index(existing_items, alias)
            if target_idx is None:
                raise ValueError("Overwrite requested but no target automation was found.")
        existing = existing_items[target_idx]
        if "id" not in automation and existing.get("id"):
            automation["id"] = existing["id"]
        if "id" not in automation:
            automation["id"] = _ensure_unique_id(slugify(alias) or "llm_automation", existing_ids)
        return automation, target_idx, warnings

    if mode not in {"create", "create_new"}:
        raise ValueError(f"Unsupported mode: {mode}")

    if "id" not in automation:
        automation["id"] = _ensure_unique_id(slugify(alias) or "llm_automation", existing_ids)

    conflict_idx = _find_automation_index(existing_items, alias) if alias else None
    if conflict_idx is not None:
        warnings.append(f"Alias conflict detected: {alias}")
        new_alias = f"{alias} ({automation['id']})"
        automation["alias"] = new_alias
        warnings.append(f"Alias renamed to: {new_alias}")

    return automation, None, warnings


async def async_create_or_update_automation(
    hass: HomeAssistant,
    yaml_text: str,
    mode: str,
    enabled: bool | None = None,
    target_identifier: str | None = None,
) -> AutomationOperationResult:
    path = Path(hass.config.path("automations.yaml"))
    items = await hass.async_add_executor_job(_load_automations_sync, path)
    try:
        automation, target_idx, warnings = _prepare_automation(yaml_text, items, enabled, mode, target_identifier)
    except Exception as err:
        return AutomationOperationResult(
            ok=False,
            mode=mode,
            automation_id=None,
            alias=None,
            entity_id=None,
            warnings=[],
            error=str(err),
        )

    if target_idx is None:
        items.append(automation)
    else:
        items[target_idx] = automation

    await hass.async_add_executor_job(_save_automations_sync, path, items)
    await hass.services.async_call("automation", "reload", blocking=True)

    automation_id = str(automation.get("id") or "")
    alias = str(automation.get("alias") or "")
    return AutomationOperationResult(
        ok=True,
        mode=mode,
        automation_id=automation_id or None,
        alias=alias or None,
        entity_id=f"automation.{automation_id}" if automation_id else None,
        warnings=warnings,
    )
