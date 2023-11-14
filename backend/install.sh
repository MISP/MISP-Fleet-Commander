#!/bin/bash

sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv screen -y

python3 -m venv venv
. ./venv/bin/activate

pip3 install -U -r requirements.txt

