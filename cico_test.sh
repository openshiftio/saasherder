#!/bin/bash

set -xe

yum -y install docker
systemctl start docker

docker build -t saasherder-test -f tests/Dockerfile.test .
docker run -it --rm saasherder-test
