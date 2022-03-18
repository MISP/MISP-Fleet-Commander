#!/bin/bash

export FLASK_APP=wsgi.py
export FLASK_DEBUG=1
export FLASK_ENV=development
export SQLALCHEMY_DATABASE_URI=sqlite:///database.db
export SQLALCHEMY_TRACK_MODIFICATIONS=1
export SECRET_KEY=secret
# export APP_CONFIG_FILE=config.ini
flask run --host=0.0.0.0
