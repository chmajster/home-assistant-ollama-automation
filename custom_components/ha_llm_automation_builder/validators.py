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


def validate_automation_yaml(yaml_text: str) -> ValidationResult:
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

    _check_entities(data, result)
    return result


def _check_entities(data: dict[str, Any], result: ValidationResult) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "entity_id" and (not isinstance(value, str) or "." not in value):
                    result.warnings.append(f"Potential invalid entity_id: {value}")
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
