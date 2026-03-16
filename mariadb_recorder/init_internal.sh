#!/usr/bin/with-contenv bash
set -euo pipefail

source /usr/lib/bashio/bashio.sh
source /scripts/lib.sh

readonly INTERNAL_DATABASE="$(bashio::config 'internal_database')"
readonly INTERNAL_USERNAME="$(bashio::config 'internal_username')"
readonly INTERNAL_PASSWORD="$(bashio::config 'internal_password')"
readonly INTERNAL_PORT="$(bashio::config 'internal_port')"

require_non_empty "internal_database" "${INTERNAL_DATABASE}"
require_non_empty "internal_username" "${INTERNAL_USERNAME}"
require_non_empty "internal_password" "${INTERNAL_PASSWORD}"

mkdir -p "${MYSQL_DATADIR}" "${MYSQL_RUN_DIR}"
chown -R mysql:mysql "${MYSQL_DATADIR}" "${MYSQL_RUN_DIR}"
chmod 750 "${MYSQL_DATADIR}" "${MYSQL_RUN_DIR}"

cat > "${MYSQL_CONFIG_FILE}" <<EOT
[mysqld]
bind-address=0.0.0.0
port=${INTERNAL_PORT}
datadir=${MYSQL_DATADIR}
socket=${MYSQL_SOCKET}
pid-file=${MYSQL_PID_FILE}
skip-name-resolve=1
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
innodb_file_per_table=1
innodb_flush_method=O_DIRECT
max_connections=200

[client]
socket=${MYSQL_SOCKET}
EOT

if [[ ! -d "${MYSQL_DATADIR}/mysql" ]]; then
  log_info "Initializing new MariaDB data directory in ${MYSQL_DATADIR}"
  mysql_install_db --user=mysql --datadir="${MYSQL_DATADIR}" --rpm >/dev/null
else
  log_info "MariaDB data directory already initialized."
fi

log_info "Starting temporary MariaDB instance for initialization checks"
mariadbd --defaults-file="${MYSQL_CONFIG_FILE}" --user=mysql --skip-networking --socket="${MYSQL_SOCKET}" &
TEMP_MYSQL_PID=$!

cleanup_temp_mysql() {
  if kill -0 "${TEMP_MYSQL_PID}" >/dev/null 2>&1; then
    mysqladmin --socket="${MYSQL_SOCKET}" -u root shutdown >/dev/null 2>&1 || true
    wait "${TEMP_MYSQL_PID}" || true
  fi
}
trap cleanup_temp_mysql EXIT

local_wait=0
while (( local_wait < 60 )); do
  if mysqladmin --socket="${MYSQL_SOCKET}" -u root ping >/dev/null 2>&1; then
    break
  fi
  sleep 2
  local_wait=$((local_wait + 2))
done

if ! mysqladmin --socket="${MYSQL_SOCKET}" -u root ping >/dev/null 2>&1; then
  log_error "Temporary MariaDB did not start correctly."
  exit 1
fi

log_info "Ensuring Home Assistant database and user exist"
mysql --socket="${MYSQL_SOCKET}" -u root <<SQL
CREATE DATABASE IF NOT EXISTS \`${INTERNAL_DATABASE}\`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${INTERNAL_USERNAME}'@'%' IDENTIFIED BY '${INTERNAL_PASSWORD}';
ALTER USER '${INTERNAL_USERNAME}'@'%' IDENTIFIED BY '${INTERNAL_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${INTERNAL_DATABASE}\`.* TO '${INTERNAL_USERNAME}'@'%';
FLUSH PRIVILEGES;
SQL

cleanup_temp_mysql
trap - EXIT

log_info "Launching MariaDB server"
exec mariadbd --defaults-file="${MYSQL_CONFIG_FILE}" --user=mysql
