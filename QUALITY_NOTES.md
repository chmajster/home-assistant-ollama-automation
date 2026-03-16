# Package Quality Notes

- Async-first implementation using Home Assistant patterns.
- Adapter architecture ready for future providers.
- Services are validated with voluptuous schemas.
- Diagnostics redact secrets.
- Unit tests cover validators, prompt builder and YAML tools.
- LLM response parsing includes layered extraction (JSON wrapper → markdown code block → plain text fallback) for better provider interoperability.
