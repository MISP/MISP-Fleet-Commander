#!/bin/bash
# Updates a manual install: code, MispQL, Python dependencies, database, web app. Stops at the first step that fails.
# Restart Fleet Commander afterwards so that its web server and workers run the new code.

set -o errexit

script_dir=$(dirname "$(realpath "$0")")
cd "$script_dir" || exit 1

git pull origin main
# MispQL is a git submodule, pinned by the commit just pulled
git submodule update --init backend/vendor/mispql

pushd backend
. ./venv/bin/activate
pip3 install -U -r requirements.txt
pip3 install --no-deps vendor/mispql
flask db upgrade
popd

# The built web app is not in git: build it again. Its dependencies first, so that a failure stops the update
# before build_web.sh removes the current build
pushd web
npm ci
popd
bash build_web.sh

echo "Updated. Restart Fleet Commander's web server and workers (the flask and workers windows of its screen session) to run the new code."
