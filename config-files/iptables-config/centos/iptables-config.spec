#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#
Summary: StarlingX iptables Configuration File
Name: iptables-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: config-files
Packager: StarlingX
URL: unknown
Source: %name-%version.tar.gz

BuildArch: noarch
Requires: iptables
Requires: iptables-services
Requires: iptables-utils

%define debug_package %{nil}

%description
StarlingX iptables configuration file

%prep

%setup

%build

%install
install -d -m 755 %{buildroot}%{_sysconfdir}/sysconfig
install -d %{buildroot}%{_datadir}/starlingx
install -m 600 iptables.rules %{buildroot}%{_datadir}/starlingx/iptables.rules
install -m 600 ip6tables.rules %{buildroot}%{_datadir}/starlingx/ip6tables.rules

%post
if [ $1 -eq 1 ] ; then
    cp -f %{_datadir}/starlingx/iptables.rules %{_sysconfdir}/sysconfig/iptables
    chmod 600 %{_sysconfdir}/sysconfig/iptables
    cp -f %{_datadir}/starlingx/ip6tables.rules %{_sysconfdir}/sysconfig/ip6tables
    chmod 600 %{_sysconfdir}/sysconfig/ip6tables
fi

%{_bindir}/systemctl enable iptables.service ip6tables.service >/dev/null 2>&1
exit 0

%files
%defattr(-,root,root)
%license LICENSE
%{_datadir}/starlingx/iptables.rules
%{_datadir}/starlingx/ip6tables.rules
