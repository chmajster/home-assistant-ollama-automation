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


def parse_yaml(yaml_text: str) -> Any:
    """Best-effort parser supporting JSON and simple YAML mappings used in tests/service checks."""
    source = yaml_text.strip()
    try:
        return json.loads(source)
    except Exception:
        pass

    result: dict[str, Any] = {}
    for line in source.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "[]":
            result[key] = []
        elif value.lower() in {"true", "false"}:
            result[key] = value.lower() == "true"
        elif value == "":
            result[key] = None
        else:
            result[key] = value.strip('"')
    if not result:
        raise ValueError("Unsupported YAML format")
    return result
