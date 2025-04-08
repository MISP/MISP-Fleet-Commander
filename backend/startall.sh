#!/bin/bash
set -o errexit

screen -dmS "mispsync-server"
sleep 0.1
screen -S "mispsync-server" -X screen -t "flask" bash -c "bash start.sh; read x"
screen -S "mispsync-server" -X screen -t "redis" bash -c "redis-server redis.conf; read x"
screen -S "mispsync-server" -X screen -t "workers" bash -c "bash start_workers.sh; read x"

