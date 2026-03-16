"""Validation utilities for generated automation YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .helpers.yaml_tools import parse_yaml


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DryRunResult:
    valid: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    trigger_matches: bool = False
    conditions_passed: bool = True
    would_execute: bool = False


def validate_automation_yaml(yaml_text: str, known_entities: set[str] | None = None) -> ValidationResult:
    result = ValidationResult(valid=True)
    try:
        data = parse_yaml(yaml_text)
    except Exception as err:  # broad by design for user-supplied YAML parsing
        return ValidationResult(valid=False, errors=[f"YAML parse error: {err}"])

    if not isinstance(data, dict):
        result.valid = False
        result.errors.append("Top-level YAML must be object/map.")
        return result

    for required in ("trigger", "action"):
        if required not in data:
            result.valid = False
            result.errors.append(f"Missing required key: {required}")

    if "alias" not in data:
        result.warnings.append("Alias missing; consider adding alias for maintainability.")

    _check_trigger_semantics(data, result)
    _check_action_semantics(data, result)
    _check_entities(data, result, known_entities)
    return result


def dry_run_automation_yaml(
    yaml_text: str,
    entity_states: dict[str, Any] | None = None,
    known_entities: set[str] | None = None,
) -> DryRunResult:
    validation = validate_automation_yaml(yaml_text, known_entities=known_entities)
    result = DryRunResult(valid=validation.valid, warnings=validation.warnings, errors=validation.errors)
    if not validation.valid:
        return result

    data = parse_yaml(yaml_text)
    entity_states = entity_states or {}
    result.trigger_matches = _simulate_trigger(data.get("trigger"), entity_states)
    result.conditions_passed = _simulate_condition(data.get("condition"), entity_states)
    result.would_execute = result.trigger_matches and result.conditions_passed
    return result


def _check_trigger_semantics(data: dict[str, Any], result: ValidationResult) -> None:
    trigger = data.get("trigger")
    if trigger is None:
        return
    nodes = trigger if isinstance(trigger, list) else [trigger]
    if not all(isinstance(item, dict) for item in nodes):
        result.valid = False
        result.errors.append("Trigger must be an object or list of objects.")
        return
    for idx, trig in enumerate(nodes):
        if "platform" not in trig:
            result.valid = False
            result.errors.append(f"Trigger #{idx + 1} missing required field: platform")


def _check_action_semantics(data: dict[str, Any], result: ValidationResult) -> None:
    action = data.get("action")
    if action is None:
        return
    nodes = action if isinstance(action, list) else [action]
    if not all(isinstance(item, dict) for item in nodes):
        result.valid = False
        result.errors.append("Action must be an object or list of objects.")
        return

    common_action_keys = {
        "service",
        "target",
        "data",
        "delay",
        "choose",
        "if",
        "then",
        "else",
        "variables",
        "repeat",
        "condition",
        "metadata",
        "alias",
        "parallel",
        "sequence",
        "device_id",
        "entity_id",
    }
    for idx, act in enumerate(nodes):
        if "service" in act and (not isinstance(act["service"], str) or "." not in act["service"]):
            result.valid = False
            result.errors.append(f"Action #{idx + 1} has invalid service format.")
        unexpected = [k for k in act if k not in common_action_keys]
        if unexpected:
            result.warnings.append(f"Action #{idx + 1} contains uncommon keys: {', '.join(unexpected)}")


def _check_entities(data: dict[str, Any], result: ValidationResult, known_entities: set[str] | None = None) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "entity_id" and (not isinstance(value, str) or "." not in value):
                    result.warnings.append(f"Potential invalid entity_id: {value}")
                if key == "entity_id" and isinstance(value, str) and known_entities and value not in known_entities:
                    result.errors.append(f"Entity does not exist in HA state registry: {value}")
                    result.valid = False
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)


def _simulate_trigger(trigger: Any, states: dict[str, Any]) -> bool:
    if not trigger:
        return True
    nodes = trigger if isinstance(trigger, list) else [trigger]
    for trig in nodes:
        if not isinstance(trig, dict):
            continue
        if trig.get("platform") != "state":
            continue
        entity_id = trig.get("entity_id")
        if not isinstance(entity_id, str) or entity_id not in states:
            continue
        expected_to = trig.get("to")
        if expected_to is None or str(states[entity_id]) == str(expected_to):
            return True
    return False


def _simulate_condition(condition: Any, states: dict[str, Any]) -> bool:
    if not condition:
        return True
    nodes = condition if isinstance(condition, list) else [condition]
    for cond in nodes:
        if not isinstance(cond, dict):
            continue
        if cond.get("condition") != "state":
            continue
        entity_id = cond.get("entity_id")
        expected_state = cond.get("state")
        if not isinstance(entity_id, str) or entity_id not in states:
            return False
        if expected_state is not None and str(states[entity_id]) != str(expected_state):
            return False
    return True
