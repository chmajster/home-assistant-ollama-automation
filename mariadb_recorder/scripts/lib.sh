#!/usr/bin/with-contenv bash
set -euo pipefail

readonly MYSQL_DATADIR="/data/mysql"
readonly MYSQL_RUN_DIR="/run/mysqld"
readonly MYSQL_SOCKET="${MYSQL_RUN_DIR}/mysqld.sock"
readonly MYSQL_PID_FILE="${MYSQL_RUN_DIR}/mysqld.pid"
readonly MYSQL_CONFIG_FILE="/tmp/my.cnf"

log_info() {
  bashio::log.info "$*"
}

log_warn() {
  bashio::log.warning "$*"
}

log_error() {
  bashio::log.error "$*"
}

sanitize() {
  local value="${1:-}"
  if [[ -z "${value}" ]]; then
    echo "<empty>"
  else
    echo "******"
  fi
}

require_non_empty() {
  local name="$1"
  local value="$2"
  if [[ -z "${value}" ]]; then
    log_error "Missing required configuration option: ${name}"
    exit 1
  fi
}

wait_for_mysql() {
  local host="$1"
  local port="$2"
  local user="$3"
  local password="$4"
  local timeout_seconds="${5:-60}"

  local elapsed=0
  while (( elapsed < timeout_seconds )); do
    if MYSQL_PWD="${password}" mysqladmin --connect-timeout=2 -h "${host}" -P "${port}" -u "${user}" ping >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done

  return 1
}

build_recorder_db_url() {
  local username="$1"
  local password="$2"
  local host="$3"
  local port="$4"
  local database="$5"
  local charset="$6"
  local collation="$7"
  local ssl_mode="$8"
  local additional_parameters="$9"

  local encoded_password
  encoded_password="$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=""))' "${password}")"

  local params="charset=${charset}&collation=${collation}"
  case "${ssl_mode}" in
    disabled) ;;
    required) params="${params}&ssl=true" ;;
    verify_ca) params="${params}&ssl=true&ssl_verify_cert=true" ;;
    verify_identity) params="${params}&ssl=true&ssl_verify_identity=true" ;;
  esac

  if [[ -n "${additional_parameters}" ]]; then
    params="${params}&${additional_parameters}"
  fi

  echo "mysql://${username}:${encoded_password}@${host}:${port}/${database}?${params}"
}

write_connection_hints() {
  local db_url="$1"
  local db_url_masked="$2"

  cat > /data/recorder_connection.txt <<EOT
# Home Assistant recorder configuration
# NOTE: Add-ons cannot reliably and safely mutate Home Assistant's configuration.yaml automatically.
# Apply the following in Home Assistant manually:

recorder:
  db_url: ${db_url}

# Sanitized version for logs:
# ${db_url_masked}
EOT
}
