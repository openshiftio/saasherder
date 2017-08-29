#!/bin/bash

set -xe

setenforce 0
yum -y install docker

sed -i.bckp "s#\# INSECURE_REGISTRY='--insecure-registry'#INSECURE_REGISTRY='--insecure-registry 172.30.0.0/16'#" /etc/sysconfig/docker

iptables -I INPUT -p tcp --dport 80   -j ACCEPT
iptables -I INPUT -p tcp --dport 443  -j ACCEPT
iptables -I INPUT -p tcp --dport 8443 -j ACCEPT
iptables -I INPUT -p udp --dport 53 -j ACCEPT

systemctl start docker

docker build -t saasherder-test -f tests/Dockerfile.test .
docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock  --privileged --net=host saasherder-test
