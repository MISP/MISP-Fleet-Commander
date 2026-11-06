#!/bin/bash
# Prepares the persistent state of a container, then runs the given command.
set -euo pipefail

DATA_DIR=/app/database
mkdir -p "$DATA_DIR" /app/data/cached-monitoring-images /app/data/pin-avatars

# The application generates its signing secret (secret_key) and its encryption key (encryption_key) in
# $DATA_DIR on first start, unless SECRET_KEY / MFC_ENCRYPTION_KEY are set

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
