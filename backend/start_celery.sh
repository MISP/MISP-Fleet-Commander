#!/bin/bash

. ./venv/bin/activate
export FLASK_APP=wsgi.py
export FLASK_DEBUG=0
export FLASK_ENV=production
export FLASK_CONFIG=config.ProductionConfig
#export SQLALCHEMY_DATABASE_URI=sqlite:///database.db
export SQLALCHEMY_DATABASE_URI=database/database.db
export SQLALCHEMY_TRACK_MODIFICATIONS=1
export SECRET_KEY=secret
export TOKEN_EXPIRATION_MIN=30
export APIKEY_EXPIRATION_DAYS=365
export AUTHLIB_INSECURE_TRANSPORT=true
celery -A application.celery worker -l INFO
