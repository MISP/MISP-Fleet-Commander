#!/bin/bash

. ./venv/bin/activate
export FLASK_APP=wsgi.py
export FLASK_DEBUG=1
export FLASK_ENV=development
export FLASK_CONFIG=config.DevelopmentConfig
export SECRET_KEY=dev_secret

flask run --port 5001
