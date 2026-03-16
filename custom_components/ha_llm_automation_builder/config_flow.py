"""Config flow for LLM Automation Builder."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_HISTORY_LIMIT,
    CONF_MAX_TOKENS,
    CONF_MODEL,
    CONF_NAME,
    CONF_OLLAMA_HOST,
    CONF_OLLAMA_PORT,
    CONF_PROVIDER,
    CONF_RESPONSE_LANGUAGE,
    CONF_SAFE_MODE,
    CONF_SYSTEM_PROMPT,
    CONF_TEMPERATURE,
    CONF_TIMEOUT,
    CONF_TOP_P,
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_MAX_TOKENS,
    DEFAULT_NAME,
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_PORT,
    PROVIDER_OLLAMA,
    PROVIDER_OPENAI_COMPATIBLE,
    DEFAULT_RESPONSE_LANGUAGE,
    DEFAULT_SAFE_MODE,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT,
    DEFAULT_TOP_P,
    DOMAIN,
)
from .helpers.errors import ModelUnavailableError, ProviderConnectionError
from .helpers.provider_runtime import build_provider_adapter, resolve_provider_base_url

PROVIDERS = [PROVIDER_OLLAMA, PROVIDER_OPENAI_COMPATIBLE]


def _connection_schema(defaults: dict[str, Any], include_name: bool) -> vol.Schema:
    schema: dict[Any, Any] = {}
    if include_name:
        schema[vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME))] = str
    schema.update(
        {
            vol.Required(CONF_PROVIDER, default=defaults.get(CONF_PROVIDER, PROVIDER_OLLAMA)): vol.In(PROVIDERS),
            vol.Optional(CONF_OLLAMA_HOST, default=defaults.get(CONF_OLLAMA_HOST, DEFAULT_OLLAMA_HOST)): str,
            vol.Required(CONF_OLLAMA_PORT, default=defaults.get(CONF_OLLAMA_PORT, DEFAULT_OLLAMA_PORT)): int,
            vol.Required(CONF_BASE_URL, default=defaults.get(CONF_BASE_URL, DEFAULT_OLLAMA_BASE_URL)): str,
            vol.Optional(CONF_API_KEY, default=defaults.get(CONF_API_KEY, "")): str,
            vol.Required(CONF_TIMEOUT, default=defaults.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)): int,
        }
    )
    return vol.Schema(schema)


def _model_schema(defaults: dict[str, Any], available_models: list[str]) -> vol.Schema:
    sorted_models = sorted(set(available_models))
    model_default = defaults.get(CONF_MODEL) or (sorted_models[0] if sorted_models else "")
    if sorted_models and model_default not in sorted_models:
        model_default = sorted_models[0]
    model_field: Any = str if not sorted_models else vol.In(sorted_models)
    return vol.Schema(
        {
            vol.Required(CONF_MODEL, default=model_default): model_field,
            vol.Required(CONF_TEMPERATURE, default=defaults.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)): vol.Coerce(float),
            vol.Required(CONF_TOP_P, default=defaults.get(CONF_TOP_P, DEFAULT_TOP_P)): vol.Coerce(float),
            vol.Required(CONF_MAX_TOKENS, default=defaults.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)): int,
            vol.Required(CONF_SYSTEM_PROMPT, default=defaults.get(CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT)): str,
            vol.Required(
                CONF_RESPONSE_LANGUAGE,
                default=defaults.get(CONF_RESPONSE_LANGUAGE, DEFAULT_RESPONSE_LANGUAGE),
            ): vol.In(["pl", "en"]),
            vol.Required(CONF_SAFE_MODE, default=defaults.get(CONF_SAFE_MODE, DEFAULT_SAFE_MODE)): bool,
            vol.Required(CONF_HISTORY_LIMIT, default=defaults.get(CONF_HISTORY_LIMIT, DEFAULT_HISTORY_LIMIT)): int,
        }
    )


async def _validate_connection(
    hass,
    user_input: dict[str, Any],
    include_name: bool,
) -> tuple[dict[str, str], dict[str, Any], list[str]]:
    errors: dict[str, str] = {}
    normalized: dict[str, Any] = dict(user_input)

    try:
        normalized[CONF_BASE_URL] = resolve_provider_base_url(
            provider=user_input[CONF_PROVIDER],
            base_url=user_input.get(CONF_BASE_URL),
            ollama_host=user_input.get(CONF_OLLAMA_HOST),
            ollama_port=user_input.get(CONF_OLLAMA_PORT),
        )
    except ValueError:
        errors[CONF_BASE_URL] = "invalid_base_url"
        return errors, normalized, []

    session = async_get_clientsession(hass)
    adapter = build_provider_adapter(
        session=session,
        provider=normalized[CONF_PROVIDER],
        base_url=normalized[CONF_BASE_URL],
        api_key=normalized.get(CONF_API_KEY) or None,
        timeout=normalized[CONF_TIMEOUT],
    )

    try:
        await adapter.test_connection()
        models = await adapter.list_models()
    except ProviderConnectionError:
        errors["base"] = "cannot_connect"
        models = []
    except Exception:
        errors["base"] = "unknown"
        models = []

    if include_name and not normalized.get(CONF_NAME):
        errors[CONF_NAME] = "required"

    return errors, normalized, models


async def _validate_selected_model(
    hass,
    config: dict[str, Any],
    model: str,
) -> dict[str, str]:
    errors: dict[str, str] = {}
    session = async_get_clientsession(hass)
    adapter = build_provider_adapter(
        session=session,
        provider=config[CONF_PROVIDER],
        base_url=config[CONF_BASE_URL],
        api_key=config.get(CONF_API_KEY) or None,
        timeout=config.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
    )
    try:
        await adapter.test_model(model)
    except ModelUnavailableError:
        errors[CONF_MODEL] = "model_not_found"
    except ProviderConnectionError:
        errors["base"] = "cannot_connect"
    except Exception:
        errors["base"] = "unknown"
    return errors


class LlmAutomationBuilderConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._connection_data: dict[str, Any] = {}
        self._available_models: list[str] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        defaults = user_input or {
            CONF_NAME: DEFAULT_NAME,
            CONF_PROVIDER: PROVIDER_OLLAMA,
            CONF_OLLAMA_HOST: DEFAULT_OLLAMA_HOST,
            CONF_OLLAMA_PORT: DEFAULT_OLLAMA_PORT,
            CONF_BASE_URL: DEFAULT_OLLAMA_BASE_URL,
            CONF_API_KEY: "",
            CONF_TIMEOUT: DEFAULT_TIMEOUT,
        }

        if user_input is not None:
            errors, normalized, models = await _validate_connection(self.hass, user_input, include_name=True)
            if not errors:
                self._connection_data = normalized
                self._available_models = models
                return await self.async_step_model()

        return self.async_show_form(
            step_id="user",
            data_schema=_connection_schema(defaults, include_name=True),
            errors=errors,
        )

    async def async_step_model(self, user_input: dict[str, Any] | None = None):
        if not self._connection_data:
            return await self.async_step_user()

        errors: dict[str, str] = {}
        defaults = user_input or {
            CONF_MODEL: self._available_models[0] if self._available_models else "",
            CONF_TEMPERATURE: DEFAULT_TEMPERATURE,
            CONF_TOP_P: DEFAULT_TOP_P,
            CONF_MAX_TOKENS: DEFAULT_MAX_TOKENS,
            CONF_SYSTEM_PROMPT: DEFAULT_SYSTEM_PROMPT,
            CONF_RESPONSE_LANGUAGE: DEFAULT_RESPONSE_LANGUAGE,
            CONF_SAFE_MODE: DEFAULT_SAFE_MODE,
            CONF_HISTORY_LIMIT: DEFAULT_HISTORY_LIMIT,
        }

        if user_input is not None:
            errors = await _validate_selected_model(self.hass, self._connection_data, user_input[CONF_MODEL])
            if not errors:
                data = {**self._connection_data, **user_input}
                if not data.get(CONF_API_KEY):
                    data.pop(CONF_API_KEY, None)
                return self.async_create_entry(title=data[CONF_NAME], data=data)

        return self.async_show_form(
            step_id="model",
            data_schema=_model_schema(defaults, self._available_models),
            errors=errors,
            description_placeholders={
                "models_count": str(len(self._available_models)),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return LlmAutomationBuilderOptionsFlow(config_entry)


class LlmAutomationBuilderOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry
        self._connection_data: dict[str, Any] = {}
        self._available_models: list[str] = []

    @property
    def _current(self) -> dict[str, Any]:
        merged = dict(self.entry.data)
        merged.update(self.entry.options or {})
        return merged

    async def async_step_init(self, user_input=None):
        errors: dict[str, str] = {}
        defaults = user_input or {
            CONF_PROVIDER: self._current.get(CONF_PROVIDER, PROVIDER_OLLAMA),
            CONF_OLLAMA_HOST: self._current.get(CONF_OLLAMA_HOST, DEFAULT_OLLAMA_HOST),
            CONF_OLLAMA_PORT: self._current.get(CONF_OLLAMA_PORT, DEFAULT_OLLAMA_PORT),
            CONF_BASE_URL: self._current.get(CONF_BASE_URL, DEFAULT_OLLAMA_BASE_URL),
            CONF_API_KEY: self._current.get(CONF_API_KEY, ""),
            CONF_TIMEOUT: self._current.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
        }

        if user_input is not None:
            validated_input = {**self._current, **user_input}
            errors, normalized, models = await _validate_connection(
                self.hass,
                validated_input,
                include_name=False,
            )
            if not errors:
                self._connection_data = normalized
                self._available_models = models
                return await self.async_step_model()

        return self.async_show_form(
            step_id="init",
            data_schema=_connection_schema(defaults, include_name=False),
            errors=errors,
        )

    async def async_step_model(self, user_input=None):
        if not self._connection_data:
            return await self.async_step_init()

        errors: dict[str, str] = {}
        defaults = user_input or {
            CONF_MODEL: self._current.get(CONF_MODEL, self._available_models[0] if self._available_models else ""),
            CONF_TEMPERATURE: self._current.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
            CONF_TOP_P: self._current.get(CONF_TOP_P, DEFAULT_TOP_P),
            CONF_MAX_TOKENS: self._current.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
            CONF_SYSTEM_PROMPT: self._current.get(CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT),
            CONF_RESPONSE_LANGUAGE: self._current.get(CONF_RESPONSE_LANGUAGE, DEFAULT_RESPONSE_LANGUAGE),
            CONF_SAFE_MODE: self._current.get(CONF_SAFE_MODE, DEFAULT_SAFE_MODE),
            CONF_HISTORY_LIMIT: self._current.get(CONF_HISTORY_LIMIT, DEFAULT_HISTORY_LIMIT),
        }

        if user_input is not None:
            errors = await _validate_selected_model(self.hass, self._connection_data, user_input[CONF_MODEL])
            if not errors:
                updated = {**self._current, **self._connection_data, **user_input}
                if not updated.get(CONF_API_KEY):
                    updated.pop(CONF_API_KEY, None)
                return self.async_create_entry(title="", data=updated)

        return self.async_show_form(
            step_id="model",
            data_schema=_model_schema(defaults, self._available_models),
            errors=errors,
            description_placeholders={
                "models_count": str(len(self._available_models)),
            },
        )
