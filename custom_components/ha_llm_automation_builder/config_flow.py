"""Config flow for LLM Automation Builder."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_HISTORY_LIMIT,
    CONF_MAX_TOKENS,
    CONF_MODEL,
    CONF_NAME,
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
    DEFAULT_RESPONSE_LANGUAGE,
    DEFAULT_SAFE_MODE,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT,
    DEFAULT_TOP_P,
    DOMAIN,
    PROVIDER_OLLAMA,
    PROVIDER_OPENAI_COMPATIBLE,
)


class LlmAutomationBuilderConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_PROVIDER, default=PROVIDER_OLLAMA): vol.In(
                    [PROVIDER_OLLAMA, PROVIDER_OPENAI_COMPATIBLE]
                ),
                vol.Required(CONF_BASE_URL): str,
                vol.Required(CONF_MODEL): str,
                vol.Optional(CONF_API_KEY): str,
                vol.Required(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): int,
                vol.Required(CONF_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.Coerce(float),
                vol.Required(CONF_TOP_P, default=DEFAULT_TOP_P): vol.Coerce(float),
                vol.Required(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): int,
                vol.Required(CONF_SYSTEM_PROMPT, default=DEFAULT_SYSTEM_PROMPT): str,
                vol.Required(CONF_RESPONSE_LANGUAGE, default=DEFAULT_RESPONSE_LANGUAGE): vol.In(["pl", "en"]),
                vol.Required(CONF_SAFE_MODE, default=DEFAULT_SAFE_MODE): bool,
                vol.Required(CONF_HISTORY_LIMIT, default=DEFAULT_HISTORY_LIMIT): int,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return LlmAutomationBuilderOptionsFlow(config_entry)


class LlmAutomationBuilderOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.entry.data, **self.entry.options}
        schema = vol.Schema(
            {
                vol.Required(CONF_MODEL, default=current.get(CONF_MODEL)): str,
                vol.Optional(CONF_API_KEY, default=current.get(CONF_API_KEY, "")): str,
                vol.Required(CONF_TIMEOUT, default=current.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)): int,
                vol.Required(
                    CONF_TEMPERATURE,
                    default=current.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
                ): vol.Coerce(float),
                vol.Required(CONF_TOP_P, default=current.get(CONF_TOP_P, DEFAULT_TOP_P)): vol.Coerce(float),
                vol.Required(CONF_MAX_TOKENS, default=current.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)): int,
                vol.Required(
                    CONF_SYSTEM_PROMPT,
                    default=current.get(CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT),
                ): str,
                vol.Required(
                    CONF_RESPONSE_LANGUAGE,
                    default=current.get(CONF_RESPONSE_LANGUAGE, DEFAULT_RESPONSE_LANGUAGE),
                ): vol.In(["pl", "en"]),
                vol.Required(CONF_SAFE_MODE, default=current.get(CONF_SAFE_MODE, DEFAULT_SAFE_MODE)): bool,
                vol.Required(
                    CONF_HISTORY_LIMIT,
                    default=current.get(CONF_HISTORY_LIMIT, DEFAULT_HISTORY_LIMIT),
                ): int,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
