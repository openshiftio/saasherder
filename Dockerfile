FROM centos:7

RUN yum install -y epel-release && \
    yum install -y python2-pip && \
    pip install --upgrade setuptools && \
    yum clean all

COPY . /saasherder

RUN cd /saasherder && \
    python setup.py install && \
    rm -rf /saasherder

RUN mkdir -p /saas
WORKDIR /saas

ENTRYPOINT ["saasherder"]
CMD []
