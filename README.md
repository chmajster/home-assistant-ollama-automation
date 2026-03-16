# ha-llm-automation-builder

Production-ready custom Home Assistant integration (HACS) for generating, validating, explaining and improving automations with local/remote LLM endpoints.

## Features
- Config Flow + Options Flow (UI-based).
- Providers: **Ollama** and **OpenAI-compatible** adapter architecture.
- Model discovery and connectivity checks.
- Services:
  - `generate_automation`
  - `validate_automation_yaml`
  - `dry_run_automation`
  - `explain_automation`
  - `improve_automation`
  - `list_available_models`
  - `generate_blueprint`
- Safe generation mode for strict YAML output.
- Prompt templates (lights, alarm, presence, heating, covers, notifications).
- Entity hints with domain filtering.
- YAML validation with warnings/errors.
- Semantic automation validation (entity existence, trigger/action sanity checks).
- Dry-run simulation service for test-before-save checks.
- Storage-backed generation history and export file output.
- Coordinator-driven sensors and binary sensor.
- Diagnostics with secret redaction.
- EN/PL translations.

## HACS installation
1. HACS → Integrations → Custom repositories.
2. Add this repository URL.
3. Category: Integration.
4. Install **LLM Automation Builder**.
5. Restart Home Assistant.
6. Add integration from UI.

## Manual installation
1. Copy `custom_components/ha_llm_automation_builder` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add integration from **Settings → Devices & Services**.

## Configuration
In config flow you can set:
- integration name
- provider (`ollama` / `openai_compatible`)
- Ollama host/IP and port (for `ollama` provider)
- base URL
- model
- optional API key
- timeout
- temperature
- top_p
- max_tokens
- system prompt
- response language (`pl`/`en`)
- safe YAML generation mode
- history size

During setup/options flow integration tests provider connection and fetches available models before model selection.

## Built-in user GUI (chat-like flow in HA)
- Text entity `automation_prompt` for entering natural-language prompt.
- Button `generate_automation_from_prompt` to generate YAML from prompt.
- Button `test_connection` to verify endpoint + selected model.
- Button `refresh_models` to load current model list.
- Button `pull_configured_model` to download configured model to Ollama.
- Generation output is exposed by sensor `ostatni_wygenerowany_yaml`.

## Example service calls
See `examples/automations/service_calls.yaml`.
Useful runtime services:
- `test_provider_connection` (optional ad-hoc provider/base URL/IP override)
- `list_available_models` (optional ad-hoc provider/base URL/IP override)
- `pull_ollama_model` (download model on Ollama endpoint)

## Troubleshooting
- Verify endpoint URL and model name using `list_available_models` service.
- Check sensor `status_llm` and binary sensor `polaczenie_ok`.
- Review diagnostics for redacted runtime state.
- If YAML fails validation, use `validate_automation_yaml` to detect semantic issues in entities/triggers/actions.
- Use `dry_run_automation` with optional `entity_states` to simulate if trigger + conditions would execute before deploying.

## Security warnings
- Prefer local endpoints for sensitive data.
- Use API keys only over trusted networks/TLS.
- Safe mode reduces but does not fully remove model risks.
- Always review generated YAML before production use.

## Home Assistant Add-on installation (Ollama Local)
1. Home Assistant -> Settings -> Add-ons -> Add-on Store -> 3-dot menu -> Repositories.
2. Add repository URL: `https://github.com/chmajster/home-assistant-ollama-automation`
3. Install add-on: **Ollama Local**.
4. Start add-on and verify it exposes port `11434`.
5. In integration config flow set:
   - provider: `ollama`
   - base URL: `http://homeassistant:11434` (or HA host IP + `:11434`)
   - model: same as add-on model option

## Configuration screenshots (placeholders)
- `![Config Flow Placeholder](docs/screenshots/config-flow-placeholder.png)`
- `![Options Flow Placeholder](docs/screenshots/options-flow-placeholder.png)`

## Package quality notes
See `QUALITY_NOTES.md`.

## Roadmap
See `ROADMAP.md`.
