#!/usr/bin/with-contenv bash
set -euo pipefail

source /usr/lib/bashio/bashio.sh
source /scripts/lib.sh

bashio::log.level "$(bashio::config 'log_level')"

MODE="$(bashio::config 'mode')"
CHARSET="$(bashio::config 'charset')"
COLLATION="$(bashio::config 'collation')"
SSL_MODE="$(bashio::config 'ssl_mode')"
ADDITIONAL_PARAMETERS="$(bashio::config 'additional_parameters')"

if [[ -z "${CHARSET}" ]]; then
  CHARSET="utf8mb4"
fi
if [[ -z "${COLLATION}" ]]; then
  COLLATION="utf8mb4_unicode_ci"
fi
if [[ -z "${SSL_MODE}" ]]; then
  SSL_MODE="disabled"
fi

log_info "Starting MariaDB Recorder Backend add-on in mode: ${MODE}"

case "${MODE}" in
  internal_mariadb)
    DB_HOST="$(bashio::addon.ip_address || true)"
    if [[ -z "${DB_HOST}" ]]; then
      DB_HOST="127.0.0.1"
    fi
    DB_PORT="$(bashio::config 'internal_port')"
    DB_DATABASE="$(bashio::config 'internal_database')"
    DB_USERNAME="$(bashio::config 'internal_username')"
    DB_PASSWORD="$(bashio::config 'internal_password')"

    require_non_empty "internal_port" "${DB_PORT}"
    require_non_empty "internal_database" "${DB_DATABASE}"
    require_non_empty "internal_username" "${DB_USERNAME}"
    require_non_empty "internal_password" "${DB_PASSWORD}"

    DB_URL="$(build_recorder_db_url "${DB_USERNAME}" "${DB_PASSWORD}" "${DB_HOST}" "${DB_PORT}" "${DB_DATABASE}" "${CHARSET}" "${COLLATION}" "${SSL_MODE}" "${ADDITIONAL_PARAMETERS}")"
    DB_URL_MASKED="$(build_recorder_db_url "${DB_USERNAME}" "$(sanitize "${DB_PASSWORD}")" "${DB_HOST}" "${DB_PORT}" "${DB_DATABASE}" "${CHARSET}" "${COLLATION}" "${SSL_MODE}" "${ADDITIONAL_PARAMETERS}")"

    write_connection_hints "${DB_URL}" "${DB_URL_MASKED}"

    log_info "Prepared Home Assistant recorder db_url (sanitized): ${DB_URL_MASKED}"
    log_info "Connection helper written to /data/recorder_connection.txt"
    log_info "Add this db_url manually in Home Assistant configuration.yaml under recorder.db_url"

    exec /init_internal.sh
    ;;

  external_mariadb)
    DB_HOST="$(bashio::config 'external_host')"
    DB_PORT="$(bashio::config 'external_port')"
    DB_DATABASE="$(bashio::config 'external_database')"
    DB_USERNAME="$(bashio::config 'external_username')"
    DB_PASSWORD="$(bashio::config 'external_password')"

    require_non_empty "external_host" "${DB_HOST}"
    require_non_empty "external_port" "${DB_PORT}"
    require_non_empty "external_database" "${DB_DATABASE}"
    require_non_empty "external_username" "${DB_USERNAME}"
    require_non_empty "external_password" "${DB_PASSWORD}"

    log_info "Validating connectivity to external MariaDB ${DB_HOST}:${DB_PORT}"
    if ! wait_for_mysql "${DB_HOST}" "${DB_PORT}" "${DB_USERNAME}" "${DB_PASSWORD}" 60; then
      log_error "Unable to connect to external MariaDB using provided credentials."
      exit 1
    fi

    DB_URL="$(build_recorder_db_url "${DB_USERNAME}" "${DB_PASSWORD}" "${DB_HOST}" "${DB_PORT}" "${DB_DATABASE}" "${CHARSET}" "${COLLATION}" "${SSL_MODE}" "${ADDITIONAL_PARAMETERS}")"
    DB_URL_MASKED="$(build_recorder_db_url "${DB_USERNAME}" "$(sanitize "${DB_PASSWORD}")" "${DB_HOST}" "${DB_PORT}" "${DB_DATABASE}" "${CHARSET}" "${COLLATION}" "${SSL_MODE}" "${ADDITIONAL_PARAMETERS}")"

    write_connection_hints "${DB_URL}" "${DB_URL_MASKED}"

    log_info "External MariaDB reachable."
    log_info "Prepared Home Assistant recorder db_url (sanitized): ${DB_URL_MASKED}"
    log_info "Connection helper written to /data/recorder_connection.txt"
    log_info "This add-on does not modify Home Assistant configuration automatically."

    exec tail -f /dev/null
    ;;

  *)
    log_error "Invalid mode: ${MODE}. Allowed values: internal_mariadb, external_mariadb"
    exit 1
    ;;
esac
