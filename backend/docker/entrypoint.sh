#!/bin/bash
# The image is started as root only long enough to fix up the ownership of the
# directories that docker bind-mounts over /app (dockerd creates missing host
# paths as root:root, and older deployments have a root-owned database.db), then
# hands over to the unprivileged mfc user. Nothing runs as root afterwards.

set -e

if [ "$(id -u)" = "0" ]; then
    chown -R mfc:mfc /app/database /app/data
    exec setpriv --reuid=mfc --regid=mfc --init-groups -- "$@"
fi

exec "$@"
