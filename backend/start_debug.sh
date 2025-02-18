#!/bin/bash

. ./venv/bin/activate
export FLASK_APP=wsgi.py
export FLASK_DEBUG=1
export FLASK_ENV=development
export FLASK_CONFIG=config.DevelopmentConfig
# export SQLALCHEMY_DATABASE_URI=database/database.db
# export SECRET_KEY=secret
# export TOKEN_EXPIRATION_MIN=30
# export APIKEY_EXPIRATION_DAYS=365
# export AUTHLIB_INSECURE_TRANSPORT=true


# export APP_CONFIG_FILE=config.ini
# flask run --host=0.0.0.0
flask run --port 5001
