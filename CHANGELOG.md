# Changelog

## 1.5.0
- Version bump.

## 1.4.0
- Added Home Assistant sidebar panel with prompt/model/params UI, result sections, and history view.
- Added HTTP API endpoints under `/api/llm_automation/*` for generate/validate/improve/history/create/modify/list/get flows.
- Added automation create/overwrite helpers that persist into `automations.yaml` and reload automations.
- Added new service calls for create/enable/overwrite/load/modify automation workflows.
- Extended history storage fields for create/modify audit metadata and diff summary.
- Updated sensor/binary_sensor names to `llm_last_yaml`, `llm_model`, `llm_status`, `llm_connection`.

## 1.3.0
- Added automatic config-entry reload after options changes so updated endpoint/model settings apply immediately.
- Version bump for integration and add-on packaging refresh.

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
