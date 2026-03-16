"""Constants for LLM Automation Builder."""

from __future__ import annotations

DOMAIN = "ha_llm_automation_builder"
PLATFORMS = ["sensor", "binary_sensor"]
VERSION = "1.0.0"

CONF_NAME = "name"
CONF_PROVIDER = "provider"
CONF_BASE_URL = "base_url"
CONF_MODEL = "model"
CONF_API_KEY = "api_key"
CONF_TIMEOUT = "timeout"
CONF_TEMPERATURE = "temperature"
CONF_TOP_P = "top_p"
CONF_MAX_TOKENS = "max_tokens"
CONF_SYSTEM_PROMPT = "system_prompt"
CONF_RESPONSE_LANGUAGE = "response_language"
CONF_SAFE_MODE = "safe_mode"
CONF_HISTORY_LIMIT = "history_limit"

PROVIDER_OLLAMA = "ollama"
PROVIDER_OPENAI_COMPATIBLE = "openai_compatible"

DEFAULT_NAME = "LLM Automation Builder"
DEFAULT_TIMEOUT = 60
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = 1200
DEFAULT_RESPONSE_LANGUAGE = "pl"
DEFAULT_SAFE_MODE = True
DEFAULT_HISTORY_LIMIT = 25
DEFAULT_SYSTEM_PROMPT = (
    "You are an expert Home Assistant automation engineer. Return valid YAML only."
)

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_history"
EXPORT_DIR = f"{DOMAIN}_exports"
COORDINATOR_UPDATE_INTERVAL_SECONDS = 60

ATTR_YAML = "yaml"
ATTR_EXPLANATION = "explanation"
ATTR_WARNINGS = "warnings"
ATTR_ASSUMPTIONS = "assumptions"
ATTR_METADATA = "metadata"
