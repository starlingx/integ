#   Expected build arguments:
#   BASE: specify base layer
#
ARG BASE

FROM ${BASE}

ENV OVS_VERSION=2.15.0

RUN apt-get -y update \
 && apt-get -y install \
    openvswitch-common \
    openvswitch-dbg \
    openvswitch-dev \
    openvswitch-ipsec \
    openvswitch-pki \
    openvswitch-switch-dpdk \
    openvswitch-switch \
    openvswitch-testcontroller \
    openvswitch-vtep