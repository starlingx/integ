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
#kubernetes-1.24.4
kubernetes-1.24.4-client
kubernetes-1.24.4-kubeadm
kubernetes-1.24.4-node
#kubernetes-1.25.3
kubernetes-1.25.3-client
kubernetes-1.25.3-kubeadm
kubernetes-1.25.3-node
#kubernetes-1.26.1
kubernetes-1.26.1-client
kubernetes-1.26.1-kubeadm
kubernetes-1.26.1-node
#kubernetes-1.27.5
kubernetes-1.27.5-client
kubernetes-1.27.5-kubeadm
kubernetes-1.27.5-node
#kubernetes-1.28.4
kubernetes-1.28.4-client
kubernetes-1.28.4-kubeadm
kubernetes-1.28.4-node
#kubernetes-1.29.2
kubernetes-1.29.2-client
kubernetes-1.29.2-kubeadm
kubernetes-1.29.2-node
#kubernetes-1.30.6
kubernetes-1.30.6-client
kubernetes-1.30.6-kubeadm
kubernetes-1.30.6-node

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

#puppet-ldap
puppet-ldap

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

#puppet-zitrlp-strongswan
puppet-zitrlp-strongswan

#python-docker
python3-docker

#python-keyring
python3-keyring

#python3-nsenter
python3-nsenter

#python3-setuptools
#python-setuptools-doc
python3-pkg-resources
python3-setuptools

#python3.9
python3.9

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
