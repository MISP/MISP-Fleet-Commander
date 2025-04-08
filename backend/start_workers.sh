#!/bin/bash

. ./venv/bin/activate
export FLASK_APP=wsgi.py
export FLASK_ENV=production
export FLASK_CONFIG=config.ProductionConfig

export WORKER_COUNT=4


huey_consumer.py application.workers.tasks.huey_app -w "$WORKER_COUNT" -k process
