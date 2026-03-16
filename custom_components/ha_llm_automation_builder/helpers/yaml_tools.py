"""YAML helpers."""

from __future__ import annotations

import json
import re
from typing import Any


def strip_markdown_fences(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```[a-zA-Z]*\n", "", cleaned)
    cleaned = re.sub(r"\n```$", "", cleaned)
    return cleaned.strip()


def extract_llm_payload_text(text: str) -> str:
    """Extract YAML-like payload from plain text, markdown blocks, or JSON wrappers."""
    source = text.strip()

    # 1) JSON wrapper formats often returned by tool calls/providers.
    try:
        parsed = json.loads(source)
    except Exception:
        parsed = None

    if parsed is not None:
        extracted = _extract_text_from_json(parsed)
        if extracted:
            source = extracted.strip()

    # 2) Markdown fenced block (prefer yaml/yml/json fences).
    fenced = re.search(r"```(?:yaml|yml|json)?\n([\s\S]*?)\n```", source, re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    # 3) Generic fence cleanup fallback.
    return strip_markdown_fences(source)


def _extract_text_from_json(payload: Any) -> str | None:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, list):
        for item in payload:
            extracted = _extract_text_from_json(item)
            if extracted:
                return extracted
        return None
    if not isinstance(payload, dict):
        return None

    for key in (
        "yaml",
        "automation_yaml",
        "improved_yaml",
        "blueprint_yaml",
        "content",
        "text",
        "response",
        "message",
    ):
        if key in payload:
            extracted = _extract_text_from_json(payload[key])
            if extracted:
                return extracted

    if "choices" in payload:
        extracted = _extract_text_from_json(payload["choices"])
        if extracted:
            return extracted

    if "delta" in payload:
        extracted = _extract_text_from_json(payload["delta"])
        if extracted:
            return extracted

    for value in payload.values():
        extracted = _extract_text_from_json(value)
        if extracted:
            return extracted
    return None


def parse_yaml(yaml_text: str) -> Any:
    """Best-effort parser supporting JSON and simple YAML mappings used in tests/service checks."""
    source = yaml_text.strip()
    try:
        return json.loads(source)
    except Exception:
        pass

    lines = [line.rstrip() for line in source.splitlines() if line.strip() and not line.strip().startswith("#")]
    if not lines:
        raise ValueError("Unsupported YAML format")

    def indent_of(line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    def parse_scalar(value: str) -> Any:
        value = value.strip()
        if value == "[]":
            return []
        if value == "{}":
            return {}
        if value.lower() in {"true", "false"}:
            return value.lower() == "true"
        if value.lower() in {"null", "none", "~"}:
            return None
        if re.fullmatch(r"-?\d+", value):
            return int(value)
        if re.fullmatch(r"-?\d+\.\d+", value):
            return float(value)
        return value.strip('"').strip("'")

    def parse_block(index: int, base_indent: int) -> tuple[Any, int]:
        if index >= len(lines):
            return {}, index
        if lines[index].lstrip().startswith("- "):
            return parse_list(index, base_indent)
        return parse_map(index, base_indent)

    def parse_map(index: int, base_indent: int) -> tuple[dict[str, Any], int]:
        result: dict[str, Any] = {}
        while index < len(lines):
            line = lines[index]
            indent = indent_of(line)
            if indent < base_indent:
                break
            if indent > base_indent:
                index += 1
                continue
            stripped = line.strip()
            if stripped.startswith("- ") or ":" not in stripped:
                break
            key, raw_value = stripped.split(":", 1)
            raw_value = raw_value.strip()
            if raw_value:
                result[key.strip()] = parse_scalar(raw_value)
                index += 1
                continue
            index += 1
            if index < len(lines) and indent_of(lines[index]) > base_indent:
                nested, index = parse_block(index, base_indent + 2)
                result[key.strip()] = nested
            else:
                result[key.strip()] = None
        return result, index

    def parse_list(index: int, base_indent: int) -> tuple[list[Any], int]:
        result: list[Any] = []
        while index < len(lines):
            line = lines[index]
            indent = indent_of(line)
            if indent < base_indent:
                break
            if indent != base_indent or not line.lstrip().startswith("- "):
                break
            item_text = line[indent + 2 :].strip()
            if not item_text:
                index += 1
                if index < len(lines) and indent_of(lines[index]) > base_indent:
                    nested, index = parse_block(index, base_indent + 2)
                    result.append(nested)
                else:
                    result.append(None)
                continue

            if ":" in item_text:
                key, raw_value = item_text.split(":", 1)
                item: dict[str, Any] = {key.strip(): parse_scalar(raw_value) if raw_value.strip() else None}
                index += 1
                while index < len(lines) and indent_of(lines[index]) > base_indent:
                    nested_indent = indent_of(lines[index])
                    if nested_indent < base_indent + 2:
                        break
                    nested_map, next_index = parse_map(index, base_indent + 2)
                    if next_index == index:
                        break
                    item.update(nested_map)
                    index = next_index
                result.append(item)
                continue

            result.append(parse_scalar(item_text))
            index += 1
        return result, index

    parsed, _ = parse_block(0, indent_of(lines[0]))
    return parsed
