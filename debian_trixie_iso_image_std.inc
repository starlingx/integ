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

#cluster-resource-agents
#ldirectord  # not used
resource-agents

#containerd
containerd

#crictl
crictl

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
librte-bus-pci25
librte-bus-vdev25
librte-cryptodev25
librte-eal25
librte-ethdev25
librte-eventdev25
librte-hash25
librte-kvargs25
librte-mbuf25
librte-mempool-ring25
librte-mempool25
librte-meter25
librte-net-bnxt25
librte-net-bond25
librte-net-dpaa25
librte-net-e1000-25
librte-net-i40e25
librte-net-ice25
librte-net-ixgbe25
librte-net-ring25
librte-net-vhost25
librte-net-virtio25
librte-net25
librte-pci25
librte-rcu25
librte-ring25
librte-telemetry25
librte-timer25
librte-vhost25

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
facter

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
libldap2
libldap-common
#libldap2-dev  # not used
#slapd-contrib  # not used
#slapd-smbk5pwd  # not used
slapd
#slapi-dev  # not used

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
puppet-agent
puppetserver

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

puppet-module-asciiduck-sssd

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

#puppetlabs-haproxy-2.1.0
puppet-module-puppetlabs-haproxy

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

#python-eventlet
python3-eventlet

#python-keyring
python3-keyring

#python3-nsenter
python3-nsenter

#pynetlink
pynetlink

#python3-pyjwkest
#python3-pyjwkest

#python3-pyoidc
#python3-pyoidc

#pyzmq
python3-zmq


#openssl
openssl
libssl3t64
libssl-dev

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
