#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#
Summary: StarlingX ntp Configuration File
Name: ntp-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: config-files
Packager: StarlingX
URL: unknown

Source0: LICENSE
Source1: ntpd.sysconfig
Source2: ntp.conf

BuildArch: noarch
Requires: ntp
Requires: ntpdate
Requires: ntp-perl

%define debug_package %{nil}

%description
StarlingX ntp configuration file

%install
install -d %{buildroot}%{_datadir}/starlingx
install -D -m644 %{SOURCE1} %{buildroot}%{_datadir}/starlingx/ntpd.sysconfig
install -D -m644 %{SOURCE2} %{buildroot}%{_datadir}/starlingx/ntp.conf

%post
if [ $1 -eq 1 ] ; then
	cp -f %{_datadir}/starlingx/ntpd.sysconfig %{_sysconfdir}/sysconfig/ntpd
	cp -f %{_datadir}/starlingx/ntp.conf %{_sysconfdir}/ntp.conf
	chmod 644 %{_sysconfdir}/sysconfig/ntpd
	chmod 644 %{_sysconfdir}/ntp.conf
fi

%preun

%postun

%files
%defattr(-,root,root)
%license ../SOURCES/LICENSE
%{_datadir}/starlingx/ntpd.sysconfig
%{_datadir}/starlingx/ntp.conf
