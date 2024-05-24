#!/bin/bash

set -o errexit

pushd backend
bash startall.sh
popd
pushd web
screen -S "mispsync-server" -X screen -t "web" bash -c "cd ../web && npm run serve; read x;"
popd

