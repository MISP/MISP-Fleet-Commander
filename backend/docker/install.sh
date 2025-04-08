#!/bin/bash

pip3 install -U -r requirements.txt
pip3 install -U -r requirements_monitoring.txt
cp config.json.sample config.json
flask db upgrade

