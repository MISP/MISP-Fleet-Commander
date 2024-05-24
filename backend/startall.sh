#!/bin/bash
set -o errexit

screen -dmS "mispsync-server"
sleep 0.1
screen -S "mispsync-server" -X screen -t "flask" bash -c "bash start.sh; read x"
screen -S "mispsync-server" -X screen -t "redis" bash -c "redis-server redis.conf; read x"
screen -S "mispsync-server" -X screen -t "celery-worker" bash -c "bash start_celery.sh; read x"
# screen -S "mispsync-server" -X screen -t "flower" bash -c ". ./venv/bin/activate && celery -A application.celery flower --port=5566"
# screen -S "mispsync-server" -X screen -t "sqlite_admin" bash -c ". ./venv/bin/activate && sqlite_web --host 127.0.0.1 --port 8088 app.db"

