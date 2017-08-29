#!/bin/bash

set -xe

yum -y install docker
systemctl start docker

docker build -t saasherder-test -f tests/Dockerfile.test .
docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock  --privileged --net=host saasherder-test
