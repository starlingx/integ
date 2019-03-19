#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#
Summary: StarlingX audit Configuration File
Name: audit-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: config-files
Packager: StarlingX
URL: unknown
Source: %name-%version.tar.gz

BuildArch: noarch
Requires: audit
Requires: audit-libs
Requires: audit-libs-python

%define debug_package %{nil}

%description
StarlingX audit configuration file

%prep

%setup

%build

%install
install -d %{buildroot}%{_datadir}/starlingx
install -m640 syslog.conf %{buildroot}%{_datadir}/starlingx/syslog.conf

%post
if [ $1 -eq 1 ] ; then
    cp -f %{_datadir}/starlingx/syslog.conf %{_sysconfdir}/audisp/plugins.d/syslog.conf
    chmod 640 %{_sysconfdir}/audisp/plugins.d/syslog.conf
fi

%files
%defattr(-,root,root)
%license LICENSE
%{_datadir}/starlingx/syslog.conf
