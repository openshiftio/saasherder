FROM fedora

RUN dnf -y install python-pip
WORKDIR /opt/saasherder

ADD . /opt/saasherder


RUN python setup.py install

