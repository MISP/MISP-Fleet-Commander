#!/bin/bash

set -o errexit

script_dir=$(dirname "$(realpath "$0")")
cd "$script_dir" || exit 1

rm -rf backend/application/dist
pushd web
npm run buildproduction
popd

