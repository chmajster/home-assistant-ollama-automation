#!/usr/bin/env bash
set -euo pipefail

OPTIONS_FILE="/data/options.json"
MODELS_DIR="/data/models"

MODEL="$(jq -r '.model // "llama3.2:3b"' "${OPTIONS_FILE}")"
AUTO_PULL="$(jq -r '.auto_pull // true' "${OPTIONS_FILE}")"
KEEP_ALIVE="$(jq -r '.keep_alive // "5m"' "${OPTIONS_FILE}")"
ORIGINS="$(jq -r '.origins // "*"' "${OPTIONS_FILE}")"

mkdir -p "${MODELS_DIR}"

export OLLAMA_MODELS="${MODELS_DIR}"
export OLLAMA_HOST="0.0.0.0:11434"
export OLLAMA_ORIGINS="${ORIGINS}"
export OLLAMA_KEEP_ALIVE="${KEEP_ALIVE}"

echo "[INFO] Starting Ollama server on ${OLLAMA_HOST}"
ollama serve &
OLLAMA_PID=$!

echo "[INFO] Waiting for Ollama API..."
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:11434/api/tags" >/dev/null; then
    break
  fi
  sleep 1
done

if [[ "${AUTO_PULL}" == "true" ]]; then
  echo "[INFO] Pulling model: ${MODEL}"
  ollama pull "${MODEL}" || echo "[WARN] Could not pull model ${MODEL}. You can pull it manually later."
fi

wait "${OLLAMA_PID}"
