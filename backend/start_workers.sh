#!/bin/bash

. ./venv/bin/activate
export FLASK_APP=wsgi.py
#export FLASK_DEBUG=0
#export FLASK_ENV=production
export FLASK_DEBUG=1
export FLASK_ENV=development
#export FLASK_CONFIG=config.ProductionConfig
export SQLALCHEMY_DATABASE_URI=database/database.db
export SQLALCHEMY_TRACK_MODIFICATIONS=1
export SECRET_KEY=secret
export TOKEN_EXPIRATION_MIN=30
export APIKEY_EXPIRATION_DAYS=365
export AUTHLIB_INSECURE_TRANSPORT=true
export WORKER_COUNT=4

# Monitoring
export GRAFANA_BASE_URL=http://localhost:3000
export GRAFANA_DASHBOARD_DATA_RENDER=render/d-solo/ce6olif96756od
export GRAFANA_DASHBOARD=d/ce6olif96756od/circl-monitoring-misp
export GRAFANA_APIKEY=glsa_k94PVSfhraGiK5roLyoniHu0xFyvByne_b1604732

huey_consumer.py application.workers.tasks.huey_app -w "$WORKER_COUNT" -k process
