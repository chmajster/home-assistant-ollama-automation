"""Service registration and handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    ATTR_ASSUMPTIONS,
    ATTR_EXPLANATION,
    ATTR_METADATA,
    ATTR_WARNINGS,
    ATTR_YAML,
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_MODEL,
    CONF_OLLAMA_HOST,
    CONF_OLLAMA_PORT,
    CONF_PROVIDER,
    CONF_TIMEOUT,
    DOMAIN,
    DEFAULT_OLLAMA_PORT,
    EXPORT_DIR,
    PROVIDER_OLLAMA,
    PROVIDER_OPENAI_COMPATIBLE,
)
from .helpers.errors import ModelUnavailableError, ProviderConnectionError
from .helpers.entity_context import collect_entities
from .helpers.provider_runtime import build_provider_adapter, resolve_provider_base_url
from .helpers.prompt_builder import build_prompt
from .helpers.yaml_tools import extract_llm_payload_text
from .llm.base import GenerationRequest
from .storage import build_history_item
from .validators import dry_run_automation_yaml, validate_automation_yaml

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

PROVIDER_OVERRIDE_FIELDS = {
    vol.Optional(CONF_PROVIDER): vol.In([PROVIDER_OLLAMA, PROVIDER_OPENAI_COMPATIBLE]),
    vol.Optional(CONF_BASE_URL): str,
    vol.Optional(CONF_OLLAMA_HOST): str,
    vol.Optional(CONF_OLLAMA_PORT, default=DEFAULT_OLLAMA_PORT): int,
    vol.Optional(CONF_API_KEY): str,
    vol.Optional(CONF_TIMEOUT): int,
}


async def async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "generate_automation"):
        return

    async def _resolve_runtime() -> Any:
        entries = list(hass.data[DOMAIN].values())
        return entries[0] if entries else None

    async def _resolve_adapter(call: ServiceCall):
        runtime = await _resolve_runtime()
        if runtime is None:
            raise HomeAssistantError("Integration is not loaded.")

        provider = call.data.get(CONF_PROVIDER, runtime.config[CONF_PROVIDER])
        try:
            base_url = resolve_provider_base_url(
                provider=provider,
                base_url=call.data.get(CONF_BASE_URL, runtime.config.get(CONF_BASE_URL)),
                ollama_host=call.data.get(CONF_OLLAMA_HOST, runtime.config.get(CONF_OLLAMA_HOST)),
                ollama_port=call.data.get(CONF_OLLAMA_PORT, runtime.config.get(CONF_OLLAMA_PORT)),
            )
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        api_key = call.data.get(CONF_API_KEY, runtime.config.get(CONF_API_KEY))
        timeout = call.data.get(CONF_TIMEOUT, runtime.config.get(CONF_TIMEOUT))

        adapter = build_provider_adapter(
            session=async_get_clientsession(hass),
            provider=provider,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )
        return runtime, provider, base_url, adapter

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
        yaml_text = extract_llm_payload_text(response.text)
        validation = validate_automation_yaml(yaml_text, known_entities=set(hass.states.async_entity_ids()))
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
        validation = validate_automation_yaml(call.data["yaml"], known_entities=set(hass.states.async_entity_ids()))
        return {"valid": validation.valid, "warnings": validation.warnings, "errors": validation.errors}

    async def dry_run(call: ServiceCall) -> ServiceResponse:
        known_entities = set(hass.states.async_entity_ids())
        entity_states = call.data.get("entity_states", {})
        result = dry_run_automation_yaml(call.data["yaml"], entity_states=entity_states, known_entities=known_entities)
        return {
            "valid": result.valid,
            "warnings": result.warnings,
            "errors": result.errors,
            "trigger_matches": result.trigger_matches,
            "conditions_passed": result.conditions_passed,
            "would_execute": result.would_execute,
        }

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
        improved = extract_llm_payload_text(response.text)
        return {"improved_yaml": improved, "diff_summary": "Model-provided improvement applied."}

    async def list_models(call: ServiceCall) -> ServiceResponse:
        _, provider, base_url, adapter = await _resolve_adapter(call)
        try:
            models = await adapter.list_models()
        except ProviderConnectionError as err:
            return {
                "ok": False,
                "provider": provider,
                "base_url": base_url,
                "models": [],
                "models_count": 0,
                "error": str(err),
            }
        return {
            "ok": True,
            "provider": provider,
            "base_url": base_url,
            "models": models,
            "models_count": len(models),
        }

    async def test_provider_connection(call: ServiceCall) -> ServiceResponse:
        runtime, provider, base_url, adapter = await _resolve_adapter(call)
        model = call.data.get(CONF_MODEL, runtime.config.get(CONF_MODEL))

        try:
            connection = await adapter.test_connection()
            models = await adapter.list_models()
            model_check = await adapter.test_model(model) if model else {"ok": False}
        except ModelUnavailableError:
            return {
                "ok": False,
                "provider": provider,
                "base_url": base_url,
                "model": model,
                "model_ok": False,
                "error": "model_not_found",
            }
        except ProviderConnectionError as err:
            return {
                "ok": False,
                "provider": provider,
                "base_url": base_url,
                "model": model,
                "model_ok": False,
                "error": str(err),
            }

        return {
            "ok": bool(connection.get("ok")),
            "provider": provider,
            "base_url": base_url,
            "model": model,
            "model_ok": bool(model_check.get("ok")),
            "models_count": len(models),
            "models": models,
        }

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
        content = extract_llm_payload_text(response.text)
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
    hass.services.async_register(
        DOMAIN,
        "dry_run_automation",
        dry_run,
        schema=vol.Schema({vol.Required("yaml"): str, vol.Optional("entity_states", default={}): dict}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(DOMAIN, "explain_automation", explain, schema=vol.Schema({vol.Required("yaml"): str}), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "improve_automation", improve, schema=vol.Schema({vol.Required("description"): str, vol.Required("yaml"): str}), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(
        DOMAIN,
        "list_available_models",
        list_models,
        schema=vol.Schema(PROVIDER_OVERRIDE_FIELDS),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "test_provider_connection",
        test_provider_connection,
        schema=vol.Schema(
            {
                **PROVIDER_OVERRIDE_FIELDS,
                vol.Optional(CONF_MODEL): str,
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(DOMAIN, "generate_blueprint", generate_blueprint, schema=vol.Schema({vol.Required("description"): str}), supports_response=SupportsResponse.ONLY)


async def async_unregister_services(hass: HomeAssistant) -> None:
    for service in (
        "generate_automation",
        "validate_automation_yaml",
        "dry_run_automation",
        "explain_automation",
        "improve_automation",
        "list_available_models",
        "test_provider_connection",
        "generate_blueprint",
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
