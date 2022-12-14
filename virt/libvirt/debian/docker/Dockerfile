# Expected build arguments:
#   BASE: specify base layer
#   REPO_OPTS: yum options to enable StarlingX repo
#
ARG BASE
FROM ${BASE} AS stx

ENV DEBIAN_FRONTEND=noninteractive

ARG PROJECT=nova
ARG UID=42424
ARG GID=42424

RUN apt-get -y update \
 && apt-get -y install \
    ceph-common \
    dmidecode \
    iptables \
    iproute2 \
    cgroup-tools \
    libcgroup1 \
    libnss-libvirt \
    libvirt0 \
    libvirt-clients \
    libvirt-daemon \
    libvirt-daemon-config-network \
    libvirt-daemon-config-nwfilter \
    libvirt-daemon-driver-lxc \
    libvirt-daemon-driver-qemu \
    libvirt-daemon-driver-storage-gluster \
    libvirt-daemon-system \
    libvirt-daemon-system-systemd \
    libvirt-login-shell \
    pm-utils \
    qemu \
    qemu-block-extra \
    qemu-system-common \
    qemu-system-data \
    qemu-system-x86 \
    qemu-guest-agent \
    openvswitch-common \
    openvswitch-switch \
    openvswitch-switch-dpdk \
    python3-openvswitch \
 && apt-get -y clean \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd -g ${GID} ${PROJECT} ;\
 useradd -u ${UID} -g ${PROJECT} -M -d /var/lib/${PROJECT} -s /usr/sbin/nologin -c "${PROJECT} user" ${PROJECT} ;\
 mkdir -p /etc/${PROJECT} /var/log/${PROJECT} /var/lib/${PROJECT} /var/cache/${PROJECT} ;\
  chown ${PROJECT}:${PROJECT} /etc/${PROJECT} /var/log/${PROJECT} /var/lib/${PROJECT} /var/cache/${PROJECT} ;\
  usermod -a -G kvm ${PROJECT} ;\
  rm -rf /var/log/* /tmp/* /var/tmp/*

