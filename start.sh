#!/bin/bash

set -o errexit

pushd backend
bash startall.sh
popd

