"""Service registration and handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse

from .const import (
    ATTR_ASSUMPTIONS,
    ATTR_EXPLANATION,
    ATTR_METADATA,
    ATTR_WARNINGS,
    ATTR_YAML,
    DOMAIN,
    EXPORT_DIR,
)
from .helpers.entity_context import collect_entities
from .helpers.prompt_builder import build_prompt
from .helpers.yaml_tools import strip_markdown_fences
from .llm.base import GenerationRequest
from .storage import build_history_item
from .validators import validate_automation_yaml

GENERATE_SCHEMA = vol.Schema(
    {
        vol.Required("description"): str,
        vol.Optional("alias"): str,
        vol.Optional("entity_hints", default=[]): [str],
        vol.Optional("existing_yaml"): str,
        vol.Optional("style", default="readable"): vol.In(["minimalist", "readable", "advanced"]),
        vol.Optional("template"): str,
    }
)


async def async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "generate_automation"):
        return

    async def _resolve_runtime() -> Any:
        entries = list(hass.data[DOMAIN].values())
        return entries[0] if entries else None

    async def generate(call: ServiceCall) -> ServiceResponse:
        runtime = await _resolve_runtime()
        entity_hints = collect_entities(call.data.get("entity_hints", []))
        prompt = build_prompt(
            user_description=call.data["description"],
            response_language=runtime.config["response_language"],
            safe_mode=runtime.config["safe_mode"],
            template=call.data.get("template"),
            entity_hints=entity_hints,
            existing_yaml=call.data.get("existing_yaml"),
            style=call.data.get("style"),
        )
        request = GenerationRequest(
            prompt=prompt,
            system_prompt=runtime.config["system_prompt"],
            model=runtime.config["model"],
            temperature=runtime.config["temperature"],
            top_p=runtime.config["top_p"],
            max_tokens=runtime.config["max_tokens"],
            timeout=runtime.config["timeout"],
        )
        response = await runtime.adapter.generate(request)
        yaml_text = strip_markdown_fences(response.text)
        validation = validate_automation_yaml(yaml_text)
        result = {
            ATTR_YAML: yaml_text,
            ATTR_EXPLANATION: "Generated automation based on your description.",
            ATTR_WARNINGS: validation.warnings,
            ATTR_ASSUMPTIONS: [],
            ATTR_METADATA: {
                "provider": runtime.config["provider"],
                "model": runtime.config["model"],
                "valid": validation.valid,
                "errors": validation.errors,
            },
        }
        runtime.last_result = result
        await runtime.history_store.async_append(
            build_history_item(runtime.config["provider"], runtime.config["model"], call.data["description"], yaml_text),
            runtime.config["history_limit"],
        )
        return result

    async def validate_yaml(call: ServiceCall) -> ServiceResponse:
        validation = validate_automation_yaml(call.data["yaml"])
        return {"valid": validation.valid, "warnings": validation.warnings, "errors": validation.errors}

    async def explain(call: ServiceCall) -> ServiceResponse:
        runtime = await _resolve_runtime()
        prompt = f"Explain this automation YAML step by step:\n{call.data['yaml']}"
        request = GenerationRequest(
            prompt=prompt,
            system_prompt=runtime.config["system_prompt"],
            model=runtime.config["model"],
            temperature=0.1,
            top_p=0.8,
            max_tokens=800,
            timeout=runtime.config["timeout"],
        )
        response = await runtime.adapter.generate(request)
        return {"explanation": response.text}

    async def improve(call: ServiceCall) -> ServiceResponse:
        runtime = await _resolve_runtime()
        prompt = f"Improve this automation:\nDescription: {call.data['description']}\nYAML:\n{call.data['yaml']}"
        request = GenerationRequest(
            prompt=prompt,
            system_prompt=runtime.config["system_prompt"],
            model=runtime.config["model"],
            temperature=runtime.config["temperature"],
            top_p=runtime.config["top_p"],
            max_tokens=runtime.config["max_tokens"],
            timeout=runtime.config["timeout"],
        )
        response = await runtime.adapter.generate(request)
        improved = strip_markdown_fences(response.text)
        return {"improved_yaml": improved, "diff_summary": "Model-provided improvement applied."}

    async def list_models(call: ServiceCall) -> ServiceResponse:
        runtime = await _resolve_runtime()
        return {"models": await runtime.adapter.list_models()}

    async def generate_blueprint(call: ServiceCall) -> ServiceResponse:
        runtime = await _resolve_runtime()
        prompt = f"Generate a Home Assistant blueprint YAML for: {call.data['description']}"
        request = GenerationRequest(
            prompt=prompt,
            system_prompt=runtime.config["system_prompt"],
            model=runtime.config["model"],
            temperature=runtime.config["temperature"],
            top_p=runtime.config["top_p"],
            max_tokens=runtime.config["max_tokens"],
            timeout=runtime.config["timeout"],
        )
        response = await runtime.adapter.generate(request)
        content = strip_markdown_fences(response.text)
        export_dir = Path(hass.config.path("storage")) / EXPORT_DIR
        export_dir.mkdir(parents=True, exist_ok=True)
        path = export_dir / "generated_blueprint.yaml"
        path.write_text(content, encoding="utf-8")
        return {"blueprint_yaml": content, "saved_to": str(path)}

    hass.services.async_register(
        DOMAIN,
        "generate_automation",
        generate,
        schema=GENERATE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(DOMAIN, "validate_automation_yaml", validate_yaml, schema=vol.Schema({vol.Required("yaml"): str}), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "explain_automation", explain, schema=vol.Schema({vol.Required("yaml"): str}), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "improve_automation", improve, schema=vol.Schema({vol.Required("description"): str, vol.Required("yaml"): str}), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "list_available_models", list_models, supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "generate_blueprint", generate_blueprint, schema=vol.Schema({vol.Required("description"): str}), supports_response=SupportsResponse.ONLY)


async def async_unregister_services(hass: HomeAssistant) -> None:
    for service in (
        "generate_automation",
        "validate_automation_yaml",
        "explain_automation",
        "improve_automation",
        "list_available_models",
        "generate_blueprint",
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
