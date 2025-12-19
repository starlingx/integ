# List of packages to be included/installed in ISO

#base-passwd
base-passwd

#bash
bash-builtins
bash-dbgsym
bash-doc
bash-static
bash

#centos-debian-compat
centos-debian-compat

#ceph
ceph-base
ceph-common
ceph-fuse
#ceph-grafana-dashboards  # not used
ceph-mds
#ceph-mgr-dashboard  # not used
#ceph-mgr-diskprediction-cloud  # not used
#ceph-mgr-diskprediction-local  # not used
#ceph-mgr-k8sevents  # not used
#ceph-mgr-rook  # not used
#ceph-mgr-ssh  # not used
ceph-mgr
ceph-mon
ceph-osd
#ceph-resource-agents  # not used
ceph
#cephfs-shell  # not used
#libcephfs-dev  # not used
#libcephfs-java  # not used
#libcephfs-jni  # not used
libcephfs2
#librados-dev  # not used
librados2
#libradospp-dev  # not used
#libradosstriper-dev  # not used
libradosstriper1
#librbd-dev  # not used
librbd1
#librgw-dev  # not used
librgw2
python3-ceph-argparse
python3-ceph
python3-cephfs
python3-rados
python3-rbd
python3-rgw
#rados-objclass-dev  # not used
radosgw
#rbd-fuse  # not used
#rbd-mirror  # not used
#rbd-nbd  # not used

#cluster-resource-agents
#ldirectord  # not used
resource-agents

#containerd
containerd

#crictl
crictl

#docker
docker.io

#dhcp
#isc-dhcp-client-ddns  # not used
isc-dhcp-client
isc-dhcp-common
#isc-dhcp-dev  # not used
#isc-dhcp-relay  # not used
#isc-dhcp-server-ldap  # not used
#isc-dhcp-server  # not used

#dnsmasq
#dnsmasq-base-lua  # not used
dnsmasq-base
dnsmasq-utils
dnsmasq

#docker-distribution
docker-registry

#dpdk
librte-bus-pci21
librte-bus-vdev21
librte-cryptodev21
librte-eal21
librte-ethdev21
librte-eventdev21
librte-hash21
librte-kvargs21
librte-mbuf21
librte-mempool-ring21
librte-mempool21
librte-meter21
librte-net-af-packet21
librte-net-af-xdp21
librte-net-ark21
librte-net-atlantic21
librte-net-axgbe21
librte-net-bnx2x21
librte-net-bnxt21
librte-net-bond21
librte-net-cxgbe21
librte-net-dpaa2-21
librte-net-dpaa21
librte-net-e1000-21
librte-net-ena21
librte-net-enetc21
librte-net-enic21
librte-net-failsafe21
librte-net-fm10k21
librte-net-hinic21
librte-net-hns3-21
librte-net-i40e21
librte-net-iavf21
librte-net-ice21
librte-net-igc21
librte-net-ipn3ke21
librte-net-ixgbe21
librte-net-kni21
librte-net-liquidio21
librte-net-memif21
librte-net-mlx4-21
librte-net-mlx5-21
librte-net-nfp21
librte-net-octeontx2-21
librte-net-octeontx21
librte-net-pcap21
librte-net-pfe21
librte-net-qede21
librte-net-ring21
librte-net-sfc21
librte-net-softnic21
librte-net-tap21
librte-net-thunderx21
librte-net-txgbe21
librte-net-vhost21
librte-net-virtio21
librte-net21
librte-pci21
librte-rcu21
librte-ring21
librte-telemetry21
librte-timer21
librte-vhost21

#drbd-tools
drbd-utils

#efitools
#efitools-dbgsym  # not used
efitools

#etcd
etcd-client
etcd-server
#golang-etcd-server-dev  # not used

#facter
#facter-dev  # not used
facter
libfacter3.14.12

#flux
flux2-charts
flux2-charts-legacy

#gpu-operator
#gpu-operator

#grub-efi
#grub-efi-amd64-bin  # not used
#grub-efi-amd64-dbg  # not used
#grub-efi-amd64-signed-template  # not used
grub-efi-amd64
#grub-efi  # not used

#grub2
grub-common
#grub-coreboot-bin  # not used
#grub-coreboot-dbg  # not used
#grub-coreboot  # not used
#grub-emu-dbg  # not used
#grub-emu  # not used
#grub-firmware-qemu  # not used
#grub-ieee1275-bin  # not used
#grub-ieee1275-dbg  # not used
#grub-ieee1275  # not used
#grub-linuxbios  # not used
grub-pc-bin
#grub-pc-dbg  # not used
grub-pc
#grub-rescue-pc  # not used
#grub-theme-starfield  # not used
#grub-xen-bin  # not used
#grub-xen-dbg  # not used
#grub-xen-host  # not used
#grub-xen  # not used
grub2-common
grub2

#grubby
grubby

#haproxy-config
haproxy
haproxy-config

#helm
helm

#ifupdown
ifupdown
ifupdown-extra

kdump-tools
crash
makedumpfile

# iputils
iputils-arping
iputils-ping
iputils-tracepath

#isolcpus-device-plugin
isolcpus-device-plugin

#k8s-pod-recovery
k8s-pod-recovery

#k8s-cni-cache-cleanup
k8s-cni-cache-cleanup

#kata-containers
kata-containers

#kubectl-cert-manager
kubectl-cert-manager

kubelogin

# lvm2
dmeventd
dmsetup
#dmsetup-udeb
libdevmapper1.02.1
#libdevmapper1.02.1-udeb
#libdevmapper-dev
libdevmapper-event1.02.1
liblvm2cmd2.03
#liblvm2-dev
lvm2
#lvm2-dbusd
#lvm2-lockd
#lvm2-udeb

#keyrings.alt
python3-keyrings.alt

#kubernetes-x (-master, -misc, -unit-test used only for build)
#kubernetes-1.29.2
kubernetes-1.29.2-client
kubernetes-1.29.2-kubeadm
kubernetes-1.29.2-node
#kubernetes-1.30.6
kubernetes-1.30.6-client
kubernetes-1.30.6-kubeadm
kubernetes-1.30.6-node
#kubernetes-1.31.5
kubernetes-1.31.5-client
kubernetes-1.31.5-kubeadm
kubernetes-1.31.5-node
#kubernetes-1.32.2
kubernetes-1.32.2-client
kubernetes-1.32.2-kubeadm
kubernetes-1.32.2-node
#kubernetes-1.33.0
kubernetes-1.33.0-client
kubernetes-1.33.0-kubeadm
kubernetes-1.33.0-node
#kubernetes-1.34.1
kubernetes-1.34.1-client
kubernetes-1.34.1-kubeadm
kubernetes-1.34.1-node

#kubernetes-unversioned
kubernetes-unversioned

#ldapscripts
ldapscripts

#libfdt
libfdt

#lighttpd
#lighttpd-doc  # not used
#lighttpd-mod-authn-gssapi  # not used
#lighttpd-mod-authn-pam  # not used
#lighttpd-mod-authn-sasl  # not used
lighttpd-mod-geoip
#lighttpd-mod-maxminddb  # not used
#lighttpd-mod-trigger-b4-dl  # not used
#lighttpd-mod-vhostdb-dbi  # not used
#lighttpd-mod-vhostdb-pgsql  # not used
#lighttpd-mod-webdav  # not used
lighttpd-modules-mysql
lighttpd

#linuxptp
linuxptp

#lldpd
#liblldpctl-dev  # not used
lldpd

#lsb
lsb-base
#lsb-release  # not used

#net-tools
net-tools

#openldap
ldap-utils
libldap-2.4-2
libldap-common
#libldap2-dev  # not used
#slapd-contrib  # not used
#slapd-smbk5pwd  # not used
slapd
#slapi-dev  # not used
slapd-ppolicy-check-password

#parted
#libparted-dev  # not used
libparted-fs-resize0
libparted-i18n
libparted2
parted-doc
parted

#luks-encryption
luks-fs-mgr

#pf-bb-config
pf-bb-config

#plugins
bond-cni
containernetworking-plugins
#golang-github-containernetworking-plugins-dev  # not used

#puppet-5.5.22
#puppet-master-passenger  # not used
puppet

#puppet-boolean-2.0.2
puppet-boolean

#puppet-ceph-3.1.1
puppet-module-ceph

#puppet-dnsmasq
puppet-dnsmasq

#puppet-drbd-0.5.2
puppet-drbd

#puppet-hash2stuff
puppet-hash2stuff

#puppet-memcached
puppet-memcached

#puppet-etcd-1.12.3
puppet-module-cristifalcas-etcd

#puppet-keystone-17.4.0
puppet-module-keystone

#puppet-module-horizon-17.4.0
puppet-module-horizon

#puppet-lvm-1.4.0
puppet-lvm

#puppet-network
puppet-network

#puppet-openstacklib-17.4.0
puppet-module-openstacklib

#puppet-oslo-17.4.0
puppet-module-oslo

#puppet-puppi
puppet-puppi

#puppet-rabbitmq-8.5.0
puppet-module-puppetlabs-rabbitmq

#puppet-staging
puppet-module-nanliu-staging

#puppetlabs-firewall-1.12.0
puppet-module-puppetlabs-firewall

#puppetlabs-haproxy-2.1.0
puppet-module-puppetlabs-haproxy

#puppetlabs-mysql-8.1.0
puppet-module-puppetlabs-mysql

#puppetlabs-postgresql-6.7.0
puppet-module-puppetlabs-postgresql

#puppetlabs-stdlib-5.0.0
puppet-module-puppetlabs-stdlib

#puppet-vswitch
puppet-module-vswitch

#puppet-zitrlp-strongswan
puppet-zitrlp-strongswan

#python-docker
python3-docker

#python3-durationpy
python3-durationpy

#python3-kubernetes
python3-kubernetes

#python-keyring
python3-keyring

#python3-nsenter
python3-nsenter

#wheel
python3-wheel

#python3.9
python3.9

#pynetlink
pynetlink

#python3-pyjwkest
python3-pyjwkest

#python3-pyoidc
python3-pyoidc

#pyzmq
python3-zmq

#openscap
libopenscap25
openscap-common
openscap-scanner
openscap-utils
python3-openscap

#openssl
openssl
libssl1.1

#openvswitch
openvswitch-common
openvswitch-switch-dpdk
openvswitch-switch

#redfishtool 1.1.8
redfishtool

#runc
#golang-github-opencontainers-runc-dev  # not used
runc

#shim-unsigned
shim-helpers-amd64-signed-template
shim-unsigned

#stalld
stalld

#synce4l
synce4l

#systemd
libnss-myhostname
#libnss-mymachines  # not used
#libnss-resolve  # not used
#libnss-systemd  # not used
libpam-systemd
#libsystemd-dev  # not used
libsystemd0
#libudev-dev  # not used
libudev1
systemd-container
#systemd-coredump  # not used
#systemd-journal-remote  # not used
systemd-sysv
#systemd-tests  # not used
#systemd-timesyncd  # not used
systemd
udev

#systemd-presets
systemd-presets

#trident-installer
trident-installer

#watchdog
watchdog

ca-certificates
