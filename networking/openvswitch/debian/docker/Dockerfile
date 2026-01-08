#   Expected build arguments:
#   BASE: specify base layer
#
ARG BASE

FROM ${BASE}

RUN apt-get -y update \
 && apt-get -y install \
    openvswitch-common \
    openvswitch-dbg \
    openvswitch-dev \
    openvswitch-ipsec \
    openvswitch-pki \
    openvswitch-switch \
    openvswitch-testcontroller \
    openvswitch-vtep \
    tini

# Ensure that tini is located at the root /tini
RUN ln -s /usr/bin/tini /tini

# Create openvswitch user/group for non-root operation
RUN groupadd -o -g 42424 openvswitch && \
    useradd -o -u 42424 -g openvswitch -M -d /var/run/openvswitch -s /sbin/nologin openvswitch

RUN rm -rf \
    /var/cache/debconf/* \
    /var/lib/apt/lists/* \
    /var/log/* \
    /tmp/* \
    /var/tmp/*
