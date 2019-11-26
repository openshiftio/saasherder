FROM centos:7

############################################################
# workaround for https://bugs.centos.org/view.php?id=16337 #
# RUN echo -e "exclude=mirror.ci.centos.org" >> /etc/yum/pluginconf.d/fastestmirror.conf
############################################################

RUN yum install -y centos-release-openshift-origin epel-release && \
    yum install -y python2-pip origin-clients openssh-clients skopeo && \
    pip install --upgrade setuptools && \
    yum clean all

COPY . /saasherder
COPY check_image.py /scripts/check_image.py

RUN cd /saasherder && \
    python setup.py install && \
    rm -rf /saasherder

RUN mkdir -p /saas
WORKDIR /saas

ENTRYPOINT ["saasherder"]
CMD []
