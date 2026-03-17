#!/bin/sh
set -eu

OPTIONS_FILE="/data/options.json"
MODELS_DIR="/data/models"

find_ollama_bin() {
  if command -v ollama >/dev/null 2>&1; then
    command -v ollama
    return 0
  fi

  for candidate in /bin/ollama /usr/bin/ollama /usr/local/bin/ollama /app/ollama; do
    if [ -x "${candidate}" ]; then
      printf "%s" "${candidate}"
      return 0
    fi
  done

  return 1
}

json_get_string() {
  key="$1"
  default="$2"

  if [ ! -f "${OPTIONS_FILE}" ]; then
    printf "%s" "${default}"
    return
  fi

  value="$(
    sed -n "s/.*\"${key}\"[[:space:]]*:[[:space:]]*\"\\([^\"]*\\)\".*/\\1/p" "${OPTIONS_FILE}" \
      | head -n 1
  )"

  if [ -n "${value}" ]; then
    printf "%s" "${value}"
  else
    printf "%s" "${default}"
  fi
}

json_get_bool() {
  key="$1"
  default="$2"

  if [ ! -f "${OPTIONS_FILE}" ]; then
    printf "%s" "${default}"
    return
  fi

  value="$(
    sed -n "s/.*\"${key}\"[[:space:]]*:[[:space:]]*\\(true\\|false\\).*/\\1/p" "${OPTIONS_FILE}" \
      | head -n 1
  )"

  if [ -n "${value}" ]; then
    printf "%s" "${value}"
  else
    printf "%s" "${default}"
  fi
}

MODEL="$(json_get_string "model" "llama3.2:3b")"
AUTO_PULL="$(json_get_bool "auto_pull" "true")"
KEEP_ALIVE="$(json_get_string "keep_alive" "5m")"
ORIGINS="$(json_get_string "origins" "*")"
OLLAMA_BIN="$(find_ollama_bin || true)"

if [ -z "${OLLAMA_BIN}" ]; then
  echo "[ERROR] Ollama binary not found in PATH or known locations."
  echo "[ERROR] PATH=${PATH:-}"
  exit 1
fi

mkdir -p "${MODELS_DIR}"

export OLLAMA_MODELS="${MODELS_DIR}"
export OLLAMA_HOST="0.0.0.0:11434"
export OLLAMA_ORIGINS="${ORIGINS}"
export OLLAMA_KEEP_ALIVE="${KEEP_ALIVE}"

echo "[INFO] Starting Ollama server on ${OLLAMA_HOST}"
"${OLLAMA_BIN}" serve &
OLLAMA_PID=$!
trap 'kill "${OLLAMA_PID}" 2>/dev/null || true' INT TERM

echo "[INFO] Waiting for Ollama API..."
READY=0
ATTEMPT=0
while [ "${ATTEMPT}" -lt 60 ]; do
  if "${OLLAMA_BIN}" list >/dev/null 2>&1; then
    READY=1
    break
  fi
  ATTEMPT=$((ATTEMPT + 1))
  sleep 1
done

if [ "${READY}" -ne 1 ]; then
  echo "[WARN] Ollama API did not become ready within 60 seconds."
fi

if [ "${AUTO_PULL}" = "true" ] && [ "${READY}" -eq 1 ]; then
  echo "[INFO] Pulling model: ${MODEL}"
  "${OLLAMA_BIN}" pull "${MODEL}" || echo "[WARN] Could not pull model ${MODEL}. You can pull it manually later."
fi

wait "${OLLAMA_PID}"
