#!/bin/bash

set -o errexit

pushd backend
bash startall.sh
popd
pushd web
npm run serve
popd

