# MariaDB Recorder Backend (Home Assistant Add-on)

Production-ready Home Assistant custom add-on for using **MariaDB** as the backend for `recorder`.

## What this add-on does

This add-on supports two modes:

1. **`internal_mariadb`**
   - installs and runs MariaDB inside the add-on container,
   - initializes persistent storage (`/data/mysql`),
   - creates Home Assistant database and dedicated DB user,
   - keeps data across restarts and updates.

2. **`external_mariadb`**
   - uses user-provided connection parameters to an external MariaDB,
   - validates connectivity and credentials at startup,
   - generates a recorder `db_url` helper.

## Requirements

- Home Assistant OS / Supervised with add-on support.
- Custom add-on repository added in Home Assistant.
- For external mode: reachable MariaDB host and credentials.

## Installation (step by step)

1. Add this repository in **Settings → Add-ons → Add-on Store → Repositories**.
2. Install **MariaDB Recorder Backend**.
3. Configure add-on options (see below).
4. Start the add-on.
5. Copy generated `db_url` into Home Assistant `configuration.yaml` (`recorder.db_url`).
6. Restart Home Assistant Core.

## Configuration

### Mode: `internal_mariadb`

Recommended options:

```yaml
mode: internal_mariadb
internal_database: homeassistant
internal_username: homeassistant
internal_password: "CHANGE_ME_STRONG_PASSWORD"
internal_port: 3306
charset: utf8mb4
collation: utf8mb4_unicode_ci
ssl_mode: disabled
additional_parameters: ""
log_level: info
```

### Mode: `external_mariadb`

```yaml
mode: external_mariadb
external_host: 192.168.1.50
external_port: 3306
external_database: homeassistant
external_username: ha_recorder
external_password: "CHANGE_ME_STRONG_PASSWORD"
charset: utf8mb4
collation: utf8mb4_unicode_ci
ssl_mode: required
additional_parameters: ""
log_level: info
```

### Option reference

- `mode`: `internal_mariadb` or `external_mariadb`
- `internal_*`: used in internal mode
- `external_*`: used in external mode
- `charset`: DB client charset (default `utf8mb4`)
- `collation`: DB collation parameter (default `utf8mb4_unicode_ci`)
- `ssl_mode`: `disabled`, `required`, `verify_ca`, `verify_identity`
- `additional_parameters`: additional URL query parameters (`k=v&k2=v2`)
- `log_level`: add-on log level

## Recorder integration (Home Assistant)

The add-on writes connection helper file:

- `/data/recorder_connection.txt`

It contains a ready-to-use `recorder` snippet.

Example for `configuration.yaml`:

```yaml
recorder:
  db_url: mysql://user:password@host:3306/homeassistant?charset=utf8mb4
```

Then restart Home Assistant Core.

## Important technical limitation

Home Assistant add-ons **do not have a fully safe, officially supported mechanism** to automatically and reliably modify Home Assistant Core `configuration.yaml` and reload recorder settings end-to-end.

Because of this platform limitation, the add-on implements the best practical semi-automatic approach:

- validates DB configuration,
- initializes internal database when needed,
- generates complete recorder `db_url`,
- writes helper file and logs sanitized connection guidance.

You must still paste/apply the final `recorder.db_url` in Home Assistant configuration yourself.

## Security notes

- No hardcoded credentials in scripts.
- Passwords come only from add-on configuration.
- Logs contain sanitized DB URL (password masked).
- Internal mode creates a dedicated DB user and grants permissions only on selected database.
- Initialization is idempotent and restart-safe.

## Persistence and updates

- Internal MariaDB data is stored in `/data/mysql` (add-on persistent storage).
- Restarting or updating add-on does not remove DB data.
- Re-running initialization is safe (uses `IF NOT EXISTS` and user `ALTER USER`).

## Troubleshooting

1. **Cannot connect in external mode**
   - verify host/port reachability,
   - verify username/password,
   - verify firewall and MariaDB bind settings.

2. **Home Assistant still writes to SQLite**
   - confirm `configuration.yaml` includes `recorder.db_url`,
   - restart Home Assistant Core.

3. **Character encoding issues**
   - use `charset=utf8mb4` and `collation=utf8mb4_unicode_ci`.

4. **Internal mode startup fails**
   - inspect add-on logs,
   - ensure password fields are not empty,
   - check that port 3306 mapping is available.

## Upgrade guidance

- Always back up Home Assistant and add-on data before upgrading.
- Upgrade add-on image.
- Confirm add-on logs show successful DB checks.
- Keep `recorder.db_url` unchanged unless credentials/host changed.

