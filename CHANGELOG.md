# Changelog

## 1.2.0
- Added GUI entities for end users: prompt text input and action buttons (generate, test connection, refresh models, pull model).
- Added service `pull_ollama_model` for downloading model on local or external Ollama endpoint.
- Added adapter-level `pull_model` support for Ollama provider.
- Added support for `button` and `text` platforms.

## 1.1.0
- Added 2-step GUI setup/options flow with provider connection test before model selection.
- Added explicit Ollama host/IP + port fields (with base URL normalization).
- Added runtime service `test_provider_connection` and expanded `list_available_models` with ad-hoc endpoint overrides.
- Added adapter timeout handling for model discovery/connection checks.
- Added provider runtime helper and unit tests for URL/IP resolution and adapter selection.

## 1.0.0
- Initial production-ready custom integration release.
- Config flow and options flow for Ollama and OpenAI-compatible endpoints.
- Service suite for generation, validation, explanation, improvement, model listing, and blueprint generation.
- Sensors and binary sensor with coordinator-driven health status.
- Prompt templates, entity context hints, YAML validation, safe mode, and storage-backed history/export.
- Diagnostics with secret redaction, translations (EN/PL), tests, fixtures, and mock responses.
