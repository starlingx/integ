#   Expected build arguments:
#   BASE: specify base layer
#
ARG BASE

FROM ${BASE}

ENV OVS_VERSION=2.11.0

RUN set -ex ;\
    yum install -y \
        bash \
        gcc \
        python2-sphinx \
        autoconf \
        automake \
        libtool \
        systemd-units \
        openssl \
        openssl-devel \
        python2-devel \
        python2-six \
        desktop-file-utils \
        groff-base \
        graphviz \
        procps-ng \
        python2-pyOpenSSL \
        nmap-ncat \
        libcap-ng \
        libcap-ng-devel \
        curl ;\
    yum clean all ;\
    TMP_DIR=$(mktemp -d) ;\
    curl -sSL http://openvswitch.org/releases/openvswitch-${OVS_VERSION}.tar.gz | tar xz -C ${TMP_DIR} --strip-components=1 ;\
    cd ${TMP_DIR} ;\
    ./boot.sh ;\
    ./configure --prefix=/usr --localstatedir=/var --sysconfdir=/etc ;\
    make ;\
    make install ;\
    cd / ;\
    rm -rf ${TMP_DIR} ;\
    yum autoremove -y \
        openssl-devel \
        python2-devel \
        libcap-ng-devel \
        gcc \
        python2-sphinx \
        autoconf \
        automake \
        libtool \
        python2-six \
        desktop-file-utils \
        groff-base \
        graphviz \
        python2-pyOpenSSL \
        nmap-ncat ;\
