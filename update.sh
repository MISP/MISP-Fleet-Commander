#!/bin/bash

git pull origin main
pushd backend
. ./venv/bin/activate
pip3 install -U -r requirements.txt
flask db upgrade
