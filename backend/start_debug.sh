#!/bin/bash

. ./venv/bin/activate
export FLASK_APP=wsgi.py
export FLASK_DEBUG=1
export FLASK_ENV=development
export SQLALCHEMY_DATABASE_URI=database/database.db
export SQLALCHEMY_TRACK_MODIFICATIONS=1
export SECRET_KEY=secret
export TOKEN_EXPIRATION_MIN=30
export APIKEY_EXPIRATION_DAYS=365
export AUTHLIB_INSECURE_TRANSPORT=true

# Monitoring
# export GRAFANA_DASHBOARD_DATA=render/d-solo/ce6olif96756od
export GRAFANA_BASE_URL=http://localhost:3000
export GRAFANA_DASHBOARD_DATA_RENDER=render/d-solo/ce6olif96756od
export GRAFANA_DASHBOARD=d/ce6olif96756od/circl-monitoring-misp
export GRAFANA_APIKEY=glsa_k94PVSfhraGiK5roLyoniHu0xFyvByne_b1604732

# export APP_CONFIG_FILE=config.ini
# flask run --host=0.0.0.0
flask run --port 5001
