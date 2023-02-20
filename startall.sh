#!/bin/bash

screen -dmS "mispsync-server"
sleep 0.1
screen -S "mispsync-server" -X screen -t "flask" bash -c "bash start.sh"
screen -S "mispsync-server" -X screen -t "sqlite_admin" bash -c ". ./venv/bin/activate && sqlite_web --host 127.0.0.1 --port 8088 app.db"

