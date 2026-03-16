"""Prompt builder logic."""

from __future__ import annotations

from ..prompts import PROMPT_TEMPLATES, SAFE_YAML_RULES


def sanitize_text(text: str, max_len: int = 4000) -> str:
    return " ".join(text.strip().split())[:max_len]


def build_prompt(
    user_description: str,
    response_language: str,
    safe_mode: bool,
    template: str | None = None,
    entity_hints: list[str] | None = None,
    existing_yaml: str | None = None,
    style: str | None = None,
) -> str:
    parts = [f"User description: {sanitize_text(user_description)}"]
    if template and template in PROMPT_TEMPLATES:
        parts.append(f"Template guidance: {PROMPT_TEMPLATES[template]}")
    if entity_hints:
        parts.append(f"Entity hints: {', '.join(entity_hints)}")
    if existing_yaml:
        parts.append(f"Existing automation YAML: {sanitize_text(existing_yaml, 6000)}")
    if style:
        parts.append(f"Requested style: {style}")
    parts.append(f"Respond in language: {response_language}")
    if safe_mode:
        parts.append(SAFE_YAML_RULES)
    parts.append("Return object-like sections: yaml, explanation, warnings, assumptions.")
    return "\n".join(parts)
