FROM centos:7

RUN yum install -y centos-release-openshift-origin epel-release && \
    yum install -y python2-pip origin-clients openssh-clients && \
    pip install --upgrade setuptools && \
    yum clean all

COPY . /saasherder
COPY check_image.py /scripts

RUN cd /saasherder && \
    python setup.py install && \
    rm -rf /saasherder

RUN mkdir -p /saas
WORKDIR /saas

ENTRYPOINT ["saasherder"]
CMD []
