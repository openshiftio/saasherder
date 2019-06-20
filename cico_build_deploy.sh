#!/bin/bash

/bin/bash cico_test.sh

DOCKER_CONF="$PWD/.docker"
mkdir -p "$DOCKER_CONF"
docker --config="$DOCKER_CONF" login -u="$QUAY_USERNAME" -p="$QUAY_PASSWORD" quay.io

make build push
