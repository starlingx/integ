# Expected build arguments:
#   BASE: specify base layer
#   REPO_OPTS: yum options to enable StarlingX repo
#
ARG BASE
FROM ${BASE}

# Location of the STX repo config file, which will be parsed for enabling repos
ARG STX_REPO_FILE=/etc/yum.repos.d/stx.repo

ARG PROJECT=nova
ARG UID=42424
ARG GID=42424

RUN set -ex ;\
    yum install --disablerepo=* \
        $(grep '^name=' ${STX_REPO_FILE} | awk -F '=' '{printf "--enablerepo=" $2 " "}') \
        -y \
        ceph-common \
        dmidecode \
        ebtables \
        iproute \
        libvirt \
        pm-utils \
        qemu \
        qemu-block-extra \
        qemu-efi \
        qemu-kvm-ev \
        qemu-kvm-tools-ev \
        perl-Error \
        perl-Data-Dumper \
        perl-TermReadKey \
        openvswitch ;\
    groupadd -g ${GID} ${PROJECT} ;\
    useradd -u ${UID} -g ${PROJECT} -M -d /var/lib/${PROJECT} -s /usr/sbin/nologin -c "${PROJECT} user" ${PROJECT} ;\
    mkdir -p /etc/${PROJECT} /var/log/${PROJECT} /var/lib/${PROJECT} /var/cache/${PROJECT} ;\
    chown ${PROJECT}:${PROJECT} /etc/${PROJECT} /var/log/${PROJECT} /var/lib/${PROJECT} /var/cache/${PROJECT} ;\
    usermod -a -G kvm ${PROJECT} ;\
    rm -rf \
        /var/log/* \
        /tmp/* \
        /var/tmp/*

