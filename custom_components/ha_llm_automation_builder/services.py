"""Service registration and handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import difflib
import time

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
    CONF_HISTORY_LIMIT,
    CONF_MAX_TOKENS,
    CONF_MODEL,
    CONF_OLLAMA_HOST,
    CONF_OLLAMA_PORT,
    CONF_PROVIDER,
    CONF_SYSTEM_PROMPT,
    CONF_TEMPERATURE,
    CONF_TIMEOUT,
    CONF_TOP_P,
    DOMAIN,
    DEFAULT_OLLAMA_PORT,
    EXPORT_DIR,
    PROVIDER_OLLAMA,
    PROVIDER_OPENAI_COMPATIBLE,
)
from .automation_manager import async_create_or_update_automation, async_get_automation
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
        vol.Optional(CONF_MODEL): str,
        vol.Optional(CONF_TEMPERATURE): vol.Coerce(float),
        vol.Optional(CONF_TOP_P): vol.Coerce(float),
        vol.Optional(CONF_MAX_TOKENS): int,
        vol.Optional(CONF_SYSTEM_PROMPT): str,
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

PULL_MODEL_SCHEMA = vol.Schema(
    {
        **PROVIDER_OVERRIDE_FIELDS,
        vol.Required(CONF_MODEL): str,
    }
)

CREATE_AUTOMATION_SCHEMA = vol.Schema(
    {
        vol.Required("yaml"): str,
        vol.Optional("enabled"): bool,
    }
)

OVERWRITE_AUTOMATION_SCHEMA = vol.Schema(
    {
        vol.Required("yaml"): str,
        vol.Required("target"): str,
        vol.Optional("enabled"): bool,
    }
)

LOAD_AUTOMATION_SCHEMA = vol.Schema(
    {
        vol.Required("target"): str,
    }
)

MODIFY_AUTOMATION_SCHEMA = vol.Schema(
    {
        vol.Required("target"): str,
        vol.Required("description"): str,
        vol.Optional("entity_hints", default=[]): [str],
        vol.Optional(CONF_MODEL): str,
        vol.Optional(CONF_TEMPERATURE): vol.Coerce(float),
        vol.Optional(CONF_TOP_P): vol.Coerce(float),
        vol.Optional(CONF_MAX_TOKENS): int,
        vol.Optional(CONF_SYSTEM_PROMPT): str,
        vol.Optional("create_mode", default="overwrite"): vol.In(["overwrite", "create_new"]),
        vol.Optional("apply_changes", default=False): bool,
        vol.Optional("enable", default=False): bool,
    }
)


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

    def _build_diff_summary(old_yaml: str, new_yaml: str) -> str:
        diff_lines = list(
            difflib.unified_diff(
                old_yaml.splitlines(),
                new_yaml.splitlines(),
                lineterm="",
            )
        )
        added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
        if added == 0 and removed == 0:
            return "No textual changes detected."
        return f"Changed lines: +{added} / -{removed}"

    async def _list_models_with_cache(runtime, provider: str, base_url: str, adapter) -> list[str]:
        cache_ttl = 30
        cache_key = f"{provider}:{base_url}"
        cache_item = runtime.model_cache.get(cache_key, {})
        if cache_item and time.time() - cache_item.get("timestamp", 0) <= cache_ttl:
            return cache_item.get("models", [])
        models = await adapter.list_models()
        runtime.model_cache[cache_key] = {"timestamp": time.time(), "models": models}
        return models

    async def generate(call: ServiceCall) -> ServiceResponse:
        runtime = await _resolve_runtime()
        last_call = runtime.model_cache.get("last_generate_ts", 0.0)
        now = time.time()
        if now - last_call < 0.3:
            raise HomeAssistantError("Rate limit: wait a moment before generating again.")
        runtime.model_cache["last_generate_ts"] = now
        entity_hints = collect_entities(call.data.get("entity_hints", []))
        model = call.data.get(CONF_MODEL, runtime.config["model"])
        temperature = call.data.get(CONF_TEMPERATURE, runtime.config["temperature"])
        top_p = call.data.get(CONF_TOP_P, runtime.config["top_p"])
        max_tokens = call.data.get(CONF_MAX_TOKENS, runtime.config["max_tokens"])
        system_prompt = call.data.get(CONF_SYSTEM_PROMPT, runtime.config["system_prompt"])
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
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
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
                "model": model,
                "valid": validation.valid,
                "errors": validation.errors,
            },
        }
        runtime.last_result = result
        await runtime.history_store.async_append(
            build_history_item(
                runtime.config["provider"],
                model,
                call.data["description"],
                yaml_text,
                explanation=result[ATTR_EXPLANATION],
                warnings=result[ATTR_WARNINGS],
            ),
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

    async def create_automation_from_yaml(call: ServiceCall) -> ServiceResponse:
        runtime = await _resolve_runtime()
        validation = validate_automation_yaml(call.data["yaml"], known_entities=set(hass.states.async_entity_ids()))
        if not validation.valid:
            return {
                "ok": False,
                "error": "validation_failed",
                "validation": {"valid": validation.valid, "errors": validation.errors, "warnings": validation.warnings},
            }
        result = await async_create_or_update_automation(
            hass=hass,
            yaml_text=call.data["yaml"],
            mode="create",
            enabled=call.data.get("enabled", False),
        )
        await runtime.history_store.async_append(
            build_history_item(
                runtime.config["provider"],
                runtime.config["model"],
                prompt="create_automation_from_yaml",
                yaml=call.data["yaml"],
                create_status="created" if result.ok else "error",
                created_automation_id=result.automation_id,
                modification_mode="create",
                warnings=result.warnings,
            ),
            runtime.config.get(CONF_HISTORY_LIMIT, 25),
        )
        return {
            "ok": result.ok,
            "mode": result.mode,
            "automation_id": result.automation_id,
            "entity_id": result.entity_id,
            "alias": result.alias,
            "warnings": result.warnings,
            "error": result.error,
        }

    async def create_and_enable_automation_from_yaml(call: ServiceCall) -> ServiceResponse:
        runtime = await _resolve_runtime()
        validation = validate_automation_yaml(call.data["yaml"], known_entities=set(hass.states.async_entity_ids()))
        if not validation.valid:
            return {
                "ok": False,
                "error": "validation_failed",
                "validation": {"valid": validation.valid, "errors": validation.errors, "warnings": validation.warnings},
            }
        result = await async_create_or_update_automation(
            hass=hass,
            yaml_text=call.data["yaml"],
            mode="create",
            enabled=True,
        )
        await runtime.history_store.async_append(
            build_history_item(
                runtime.config["provider"],
                runtime.config["model"],
                prompt="create_and_enable_automation_from_yaml",
                yaml=call.data["yaml"],
                create_status="created_enabled" if result.ok else "error",
                created_automation_id=result.automation_id,
                modification_mode="create",
                warnings=result.warnings,
            ),
            runtime.config.get(CONF_HISTORY_LIMIT, 25),
        )
        return {
            "ok": result.ok,
            "mode": result.mode,
            "automation_id": result.automation_id,
            "entity_id": result.entity_id,
            "alias": result.alias,
            "warnings": result.warnings,
            "error": result.error,
        }

    async def overwrite_automation_from_yaml(call: ServiceCall) -> ServiceResponse:
        runtime = await _resolve_runtime()
        validation = validate_automation_yaml(call.data["yaml"], known_entities=set(hass.states.async_entity_ids()))
        if not validation.valid:
            return {
                "ok": False,
                "error": "validation_failed",
                "validation": {"valid": validation.valid, "errors": validation.errors, "warnings": validation.warnings},
            }
        result = await async_create_or_update_automation(
            hass=hass,
            yaml_text=call.data["yaml"],
            mode="overwrite",
            enabled=call.data.get("enabled"),
            target_identifier=call.data["target"],
        )
        await runtime.history_store.async_append(
            build_history_item(
                runtime.config["provider"],
                runtime.config["model"],
                prompt=f"overwrite:{call.data['target']}",
                yaml=call.data["yaml"],
                create_status="overwritten" if result.ok else "error",
                created_automation_id=result.automation_id,
                source_automation_id=call.data["target"],
                modification_mode="overwrite",
                warnings=result.warnings,
            ),
            runtime.config.get(CONF_HISTORY_LIMIT, 25),
        )
        return {
            "ok": result.ok,
            "mode": result.mode,
            "automation_id": result.automation_id,
            "entity_id": result.entity_id,
            "alias": result.alias,
            "warnings": result.warnings,
            "error": result.error,
        }

    async def load_existing_automation(call: ServiceCall) -> ServiceResponse:
        item = await async_get_automation(hass, call.data["target"])
        if item is None:
            return {"ok": False, "error": "automation_not_found", "target": call.data["target"]}
        return {"ok": True, **item}

    async def modify_automation_with_ollama(call: ServiceCall) -> ServiceResponse:
        runtime = await _resolve_runtime()
        last_call = runtime.model_cache.get("last_modify_ts", 0.0)
        now = time.time()
        if now - last_call < 0.3:
            raise HomeAssistantError("Rate limit: wait a moment before modifying again.")
        runtime.model_cache["last_modify_ts"] = now
        source = await async_get_automation(hass, call.data["target"])
        if source is None:
            return {"ok": False, "error": "automation_not_found", "target": call.data["target"]}

        model = call.data.get(CONF_MODEL, runtime.config["model"])
        temperature = call.data.get(CONF_TEMPERATURE, runtime.config["temperature"])
        top_p = call.data.get(CONF_TOP_P, runtime.config["top_p"])
        max_tokens = call.data.get(CONF_MAX_TOKENS, runtime.config["max_tokens"])
        system_prompt = call.data.get(CONF_SYSTEM_PROMPT, runtime.config["system_prompt"])

        entity_hints = collect_entities(call.data.get("entity_hints", []))
        prompt = build_prompt(
            user_description=call.data["description"],
            response_language=runtime.config["response_language"],
            safe_mode=runtime.config["safe_mode"],
            entity_hints=entity_hints,
            existing_yaml=source["yaml"],
            style="advanced",
        )
        request = GenerationRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            timeout=runtime.config["timeout"],
        )
        response = await runtime.adapter.generate(request)
        improved_yaml = extract_llm_payload_text(response.text)
        validation = validate_automation_yaml(improved_yaml, known_entities=set(hass.states.async_entity_ids()))
        diff_summary = _build_diff_summary(source["yaml"], improved_yaml)

        apply_changes = bool(call.data.get("apply_changes", False))
        create_mode = call.data.get("create_mode", "overwrite")
        apply_result: dict[str, Any] | None = None
        if apply_changes and validation.valid:
            if create_mode == "overwrite":
                save = await async_create_or_update_automation(
                    hass=hass,
                    yaml_text=improved_yaml,
                    mode="overwrite",
                    enabled=call.data.get("enable"),
                    target_identifier=source["id"] or source["alias"] or call.data["target"],
                )
            else:
                save = await async_create_or_update_automation(
                    hass=hass,
                    yaml_text=improved_yaml,
                    mode="create_new",
                    enabled=call.data.get("enable", False),
                )
            apply_result = {
                "ok": save.ok,
                "mode": save.mode,
                "automation_id": save.automation_id,
                "entity_id": save.entity_id,
                "alias": save.alias,
                "warnings": save.warnings,
                "error": save.error,
            }
        elif apply_changes and not validation.valid:
            apply_result = {
                "ok": False,
                "error": "validation_failed",
                "validation": {"valid": validation.valid, "errors": validation.errors, "warnings": validation.warnings},
            }

        await runtime.history_store.async_append(
            build_history_item(
                runtime.config["provider"],
                model,
                prompt=call.data["description"],
                yaml=improved_yaml,
                explanation="Modified existing automation with model assistance.",
                warnings=validation.warnings,
                create_status=("applied" if apply_result and apply_result.get("ok") else "preview"),
                created_automation_id=(apply_result or {}).get("automation_id") if apply_result else None,
                source_automation_id=source["id"] or source["alias"],
                modification_mode=create_mode,
                diff_summary=diff_summary,
            ),
            runtime.config.get(CONF_HISTORY_LIMIT, 25),
        )

        return {
            "ok": True,
            "target": call.data["target"],
            "source_automation": source,
            "improved_yaml": improved_yaml,
            "explanation": "Modified existing automation according to your prompt.",
            "warnings": validation.warnings,
            "validation": {
                "valid": validation.valid,
                "errors": validation.errors,
            },
            "diff_summary": diff_summary,
            "apply_result": apply_result,
        }

    async def list_models(call: ServiceCall) -> ServiceResponse:
        runtime, provider, base_url, adapter = await _resolve_adapter(call)
        try:
            models = await _list_models_with_cache(runtime, provider, base_url, adapter)
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
            models = await _list_models_with_cache(runtime, provider, base_url, adapter)
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

    async def pull_ollama_model(call: ServiceCall) -> ServiceResponse:
        runtime, provider, base_url, adapter = await _resolve_adapter(call)
        model = call.data.get(CONF_MODEL)
        if provider != PROVIDER_OLLAMA:
            return {
                "ok": False,
                "provider": provider,
                "base_url": base_url,
                "model": model,
                "error": "pull_supported_only_for_ollama",
            }

        try:
            pull_result = await adapter.pull_model(model)
            runtime.model_cache.pop(f"{provider}:{base_url}", None)
            models = await _list_models_with_cache(runtime, provider, base_url, adapter)
        except ProviderConnectionError as err:
            return {
                "ok": False,
                "provider": provider,
                "base_url": base_url,
                "model": model,
                "error": str(err),
            }

        return {
            "ok": True,
            "provider": provider,
            "base_url": base_url,
            "model": model,
            "models_count": len(models),
            "models": models,
            "pull_result": pull_result,
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
    hass.services.async_register(
        DOMAIN,
        "pull_ollama_model",
        pull_ollama_model,
        schema=PULL_MODEL_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "create_automation_from_yaml",
        create_automation_from_yaml,
        schema=CREATE_AUTOMATION_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "create_and_enable_automation_from_yaml",
        create_and_enable_automation_from_yaml,
        schema=vol.Schema({vol.Required("yaml"): str}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "overwrite_automation_from_yaml",
        overwrite_automation_from_yaml,
        schema=OVERWRITE_AUTOMATION_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "load_existing_automation",
        load_existing_automation,
        schema=LOAD_AUTOMATION_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "modify_automation_with_ollama",
        modify_automation_with_ollama,
        schema=MODIFY_AUTOMATION_SCHEMA,
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
        "pull_ollama_model",
        "create_automation_from_yaml",
        "create_and_enable_automation_from_yaml",
        "overwrite_automation_from_yaml",
        "load_existing_automation",
        "modify_automation_with_ollama",
        "generate_blueprint",
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
