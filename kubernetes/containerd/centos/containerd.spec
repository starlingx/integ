# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#
Name: containerd
Version: 1.4.11
Release: %{tis_patch_ver}%{?_tis_dist}
Summary: Open and reliable container runtime
Group: Kubernetes
License: ASL 2.0
Source0: containerd-v%{version}.tar.gz
Source1: runc-1.0.2.tar.gz
Source2: crictl-v1.21.0-linux-amd64.tar.gz
Source3: crictl.yaml
Source4: k8s-container-cleanup.sh
Patch1: 0001-customize-containerd-for-StarlingX.patch
Patch2: 0002-CRI-Reduce-clutter-of-log-entries-during-process-exe.patch
URL: https://www.starlingx.io
Vendor: StarlingX
Packager: StarlingX

BuildRequires: pkgconfig(systemd)
BuildRequires: pkgconfig(libseccomp)
BuildRequires: pkgconfig(libsystemd-journal)

# Build with our own prefered golang
BuildRequires: golang >= 1.16.8

BuildRequires: systemd
BuildRequires: rsync
BuildRequires: go-md2man
BuildRequires: go-bindata
BuildRequires: rpm-devel >= 4.14.0
BuildRequires: rpm-libs >= 4.14.0

# required packages on install
Requires: /bin/sh
Requires: systemd

Provides: containerd
Provides: runc
Provides: containerd.io


%global _missing_build_ids_terminate_build 0

%define local_sbindir /usr/local/sbin
%define CONTAINERD_DIR ${HOME}/go/src/github.com/containerd/containerd
%define RUNC_DIR ${HOME}/go/src/github.com/opencontainers/runc

%description
Containerd is an industry-standard container runtime with an emphasis on
simplicity, robustness and portability. It is available as a daemon for Linux
and Windows, which can manage the complete container lifecycle of its host
system: image transfer and storage, container execution and supervision,
low-level storage and network attachments, etc.

%prep
%setup -q -c -n src -a 1
%setup -q -c -T -D -n src -a 2
%patch1 -p1
%patch2 -p1

%build
# build containerd
rm -rf %{CONTAINERD_DIR}
mkdir -p %{CONTAINERD_DIR}
cp -a %{_builddir}/src/containerd/* %{CONTAINERD_DIR}/
pushd %{CONTAINERD_DIR}
go env -w GO111MODULE=auto
make
popd

# build runc
rm -rf %{RUNC_DIR}
mkdir -p %{RUNC_DIR}
cp -a %{_builddir}/src/runc/* %{RUNC_DIR}/
pushd %{RUNC_DIR}
make
popd

%install
# install containerd
install -d %{buildroot}%{_bindir}
install -p -m 755 %{CONTAINERD_DIR}/bin/containerd %{buildroot}%{_bindir}/containerd
install -d  %{buildroot}%{_prefix}/local/bin
ln -s  %{_bindir}/containerd %{buildroot}%{_prefix}/local/bin/containerd
install -p -m 755 %{CONTAINERD_DIR}/bin/containerd-shim %{buildroot}%{_bindir}/containerd-shim
install -p -m 755 %{CONTAINERD_DIR}/bin/containerd-shim-runc-v1 %{buildroot}%{_bindir}/containerd-shim-runc-v1
install -p -m 755 %{CONTAINERD_DIR}/bin/containerd-shim-runc-v2 %{buildroot}%{_bindir}/containerd-shim-runc-v2
install -p -m 755 %{CONTAINERD_DIR}/bin/containerd-stress %{buildroot}%{_bindir}/containerd-stress
install -p -m 755 %{CONTAINERD_DIR}/bin/ctr %{buildroot}%{_bindir}/ctr
install -p -m 755 %{RUNC_DIR}/runc %{buildroot}%{_bindir}/runc
install -p -m 755 %{_builddir}/src/crictl %{buildroot}%{_bindir}/crictl
install -d %{buildroot}%{_sysconfdir}
install -m 644 %{_sourcedir}/crictl.yaml %{buildroot}%{_sysconfdir}/crictl.yaml
install -d %{buildroot}%{_unitdir}
install -p -m 644 %{CONTAINERD_DIR}/containerd.service %{buildroot}%{_unitdir}/containerd.service
install -d %{buildroot}%{local_sbindir}
install -m 755 %{SOURCE4} %{buildroot}%{local_sbindir}/k8s-container-cleanup

# list files owned by the package here
%files
%{_prefix}/local/bin/containerd
%{_bindir}/containerd
%{_bindir}/containerd-shim
%{_bindir}/containerd-shim-runc-v1
%{_bindir}/containerd-shim-runc-v2
%{_bindir}/containerd-stress
%{_bindir}/ctr
%{_bindir}/runc
%{_bindir}/crictl
%{_sysconfdir}/crictl.yaml
%{_unitdir}/containerd.service
%{local_sbindir}/k8s-container-cleanup
