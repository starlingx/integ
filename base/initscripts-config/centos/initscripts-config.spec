#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#
Summary: initscripts-config
Name: initscripts-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Requires: %{_bindir}/systemctl
Requires: initscripts
Summary: package StarlingX configuration files of initscripts to system folder.

%description
package StarlingX configuration files of initscripts to system folder.

%prep
%setup

%build

%install
%{__install} -d  644 %{buildroot}%{_datadir}/starlingx/
%{__install} -d  644 %{buildroot}%{_sysconfdir}/sysconfig
%{__install} -d  755 %{buildroot}%{_initddir}
%{__install} -d  644 %{buildroot}%{_unitdir}

%{__install} -m  644 sysctl.conf              %{buildroot}%{_datadir}/starlingx/stx.sysctl.conf
%{__install} -m  644 sysconfig-network.conf   %{buildroot}%{_sysconfdir}/sysconfig/network
%{__install} -m  755 mountnfs.sh              %{buildroot}%{_initddir}/mountnfs
%{__install} -m  644 mountnfs.service         %{buildroot}%{_unitdir}/mountnfs.service

%post
if [ $1 -eq 1 ] ; then
        # Initial installation
        cp -f %{_datadir}/starlingx/stx.sysctl.conf %{_sysconfdir}/sysctl.conf
        chmod 644 %{_sysconfdir}/sysctl.conf
fi
%{_bindir}/systemctl enable mountnfs.service  > /dev/null 2>&1 || :

%files
%{_datadir}/starlingx/stx.sysctl.conf
%{_sysconfdir}/sysconfig/network
%{_initddir}/mountnfs
%{_unitdir}/mountnfs.service
