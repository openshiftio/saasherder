#!/bin/bash

set -xe

setenforce 0
yum -y install docker

sed -i.bckp '/OPTIONS=.*/c\OPTIONS="--selinux-enabled --insecure-registry 172.30.0.0/16"' /etc/sysconfig/docker

iptables -I INPUT -p tcp --dport 80   -j ACCEPT
iptables -I INPUT -p tcp --dport 443  -j ACCEPT
iptables -I INPUT -p tcp --dport 8443 -j ACCEPT
iptables -I INPUT -p udp --dport 53 -j ACCEPT

systemctl start docker

make test
