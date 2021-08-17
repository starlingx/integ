#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#
Summary: isolcpus-device-plugin 
Name: isolcpus-device-plugin
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River
URL: unknown
BuildArch: x86_64 
Source: %name-%version.tar.gz

# Build with our own prefered golang, not 1.11 from CentOS
# BuildRequires: golang
BuildRequires: golang >= 1.13

BuildRequires: systemd
Requires: kubernetes-node
Summary: Kubernetes device plugin for isolcpus 

%description
Expose isolated CPUs to Kubernetes as devices via the device plugin API

%define local_etc_pmond /etc/pmon.d/

%prep
%autosetup

# The "-mod=vendor" bit is because we want to use the dependencies from the vendor
# directory rather than downloading them on the fly.  The "-ldflags=-linkmode=external"
# is there to work around the fact that the RPM infrastructure wants to see
# a ".note.gnu.build-id" build ID, but "go build" gives a ".note.go.build-id" build ID.
%build
go build -mod=vendor -ldflags=-linkmode=external

%install
mkdir -p %{buildroot}%{_exec_prefix}/local/sbin
install -m 755 isolcpu_plugin %{buildroot}%{_exec_prefix}/local/sbin/isolcpu_plugin
mkdir -p %{buildroot}%{_unitdir}
install -m 644 isolcpu_plugin.service %{buildroot}%{_unitdir}/isolcpu_plugin.service
mkdir -p %{buildroot}%{local_etc_pmond}
install -m 644 isolcpu_plugin.conf %{buildroot}%{local_etc_pmond}/isolcpu_plugin.conf


%files
%{_exec_prefix}/local/sbin/isolcpu_plugin
%{_unitdir}/isolcpu_plugin.service
%{local_etc_pmond}/isolcpu_plugin.conf

# Enable the service and start it.
%post
if [ $1 -eq 1 ] ; then 
        # Initial installation 
        systemctl enable --now isolcpu_plugin.service >/dev/null 2>&1 || : 
fi 


# Disable the service and stop it.
%preun
%systemd_preun isolcpu_plugin.service

# Try to restart the service.  Usefull for RPM package upgrades during patching.
%postun
%systemd_postun_with_restart isolcpu_plugin.service
exit 0
