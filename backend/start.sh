#!/bin/bash

. ./venv/bin/activate
export FLASK_APP=wsgi.py
export FLASK_ENV=production
export FLASK_CONFIG=config.ProductionConfig
# export TOKEN_EXPIRATION_MIN=30
# export APIKEY_EXPIRATION_DAYS=365
# export AUTHLIB_INSECURE_TRANSPORT=true

flask run --host=0.0.0.0 --port 5001
