#!/bin/bash

. ./venv/bin/activate
export FLASK_APP=wsgi.py
export FLASK_DEBUG=1
export FLASK_ENV=development
export FLASK_CONFIG=config.DevelopmentConfig
export SECRET_KEY=dev_secret
# The dev frontend is served by `npm run serve` on another origin
export SOCKETIO_CORS_ALLOWED_ORIGINS=http://localhost:8080

flask run --port 5001
