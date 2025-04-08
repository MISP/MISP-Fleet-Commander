#!/bin/bash

apt update && apt upgrade -y
apt install python3-pip python3-venv screen redis-server -y

python3 -m venv venv
. ./venv/bin/activate

pip3 install -U -r requirements.txt
cp config.json.sample config.json
flask db upgrade

