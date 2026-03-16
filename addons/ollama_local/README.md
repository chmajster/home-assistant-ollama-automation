# Ollama Local

This add-on runs a local Ollama server inside Home Assistant Supervisor.

Supported architectures: `amd64`, `aarch64`.

## What it does
- Starts `ollama serve` on port `11434`.
- Optionally pulls a model at startup (`auto_pull: true`).
- Stores downloaded models in add-on persistent storage (`/data/models`).

## Options
- `model` (string): model name to auto-pull, e.g. `llama3.2:3b`.
- `auto_pull` (bool): pull model on startup.
- `keep_alive` (string): value for `OLLAMA_KEEP_ALIVE`, e.g. `5m` or `30m`.
- `origins` (string): value for `OLLAMA_ORIGINS` (CORS), default `*`.

## Use with this repository integration
In `LLM Automation Builder` config flow:
- Provider: `ollama`
- Base URL: `http://homeassistant:11434` or your HA host IP with port `11434`
- Model: same as add-on option `model`

If your Home Assistant installation/network layout differs, use the endpoint reachable from HA Core container.
