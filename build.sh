#!/bin/bash

set -o errexit

script_dir=$(dirname "$(realpath "$0")")
cd "$script_dir" || exit 1

rm backend/application/dist.zip 
rm -r backend/application/dist
pushd web
npm run buildproduction
popd
pushd backend/application/
zip -r dist.zip dist

