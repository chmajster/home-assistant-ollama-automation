# ha-llm-automation-builder

Production-ready custom Home Assistant integration (HACS) for generating, validating, explaining and improving automations with local/remote LLM endpoints.

## Features
- Config Flow + Options Flow (UI-based).
- Providers: **Ollama** and **OpenAI-compatible** adapter architecture.
- Model discovery and connectivity checks.
- Services:
  - `generate_automation`
  - `validate_automation_yaml`
  - `explain_automation`
  - `improve_automation`
  - `list_available_models`
  - `generate_blueprint`
- Safe generation mode for strict YAML output.
- Prompt templates (lights, alarm, presence, heating, covers, notifications).
- Entity hints with domain filtering.
- YAML validation with warnings/errors.
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

## Example service calls
See `examples/automations/service_calls.yaml`.

## Troubleshooting
- Verify endpoint URL and model name using `list_available_models` service.
- Check sensor `status_llm` and binary sensor `polaczenie_ok`.
- Review diagnostics for redacted runtime state.
- If YAML fails validation, use `validate_automation_yaml` and improve prompt clarity.

## Security warnings
- Prefer local endpoints for sensitive data.
- Use API keys only over trusted networks/TLS.
- Safe mode reduces but does not fully remove model risks.
- Always review generated YAML before production use.

## Configuration screenshots (placeholders)
- `![Config Flow Placeholder](docs/screenshots/config-flow-placeholder.png)`
- `![Options Flow Placeholder](docs/screenshots/options-flow-placeholder.png)`

## Package quality notes
See `QUALITY_NOTES.md`.

## Roadmap
See `ROADMAP.md`.
