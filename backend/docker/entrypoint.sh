#!/bin/bash
# Prepares the persistent state of a container, then runs the given command.
set -euo pipefail

DATA_DIR=/app/database
mkdir -p "$DATA_DIR" /app/data/cached-monitoring-images /app/data/pin-avatars

# Secret used to sign the session tokens: generated once and kept in the data volume
# so tokens survive restarts. An explicit SECRET_KEY environment variable wins.
if [ -z "${SECRET_KEY:-}" ]; then
    if [ ! -s "$DATA_DIR/secret_key" ]; then
        python -c 'import secrets; print(secrets.token_hex(32))' > "$DATA_DIR/secret_key"
        chmod 600 "$DATA_DIR/secret_key"
    fi
    SECRET_KEY="$(cat "$DATA_DIR/secret_key")"
    export SECRET_KEY
fi

# Instance settings are edited from the UI: keep them in the data volume
if [ ! -f "$DATA_DIR/config.json" ]; then
    cp /app/config.json.sample "$DATA_DIR/config.json"
fi
ln -sf "$DATA_DIR/config.json" /app/config.json

# Only one service should migrate the database (the backend, see docker-compose.yml)
if [ "${MFC_RUN_MIGRATIONS:-0}" = "1" ]; then
    flask db upgrade
fi

exec "$@"
