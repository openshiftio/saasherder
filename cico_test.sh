#!/bin/bash

set -xe

docker build -t saasherder-test -f tests/Dockerfile.test .
docker run -it --rm saasherder-test
