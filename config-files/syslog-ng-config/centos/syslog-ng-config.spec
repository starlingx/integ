#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#
Summary: StarlingX syslog-ng Configuration File
Name: syslog-ng-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: config-files
Packager: StarlingX
URL: unknown
Source: %name-%version.tar.gz

BuildArch: noarch
# systemd provides %{_unitdir}
BuildRequires: systemd
Requires: syslog-ng
Requires: syslog-ng-libdbi

%define debug_package %{nil}

%description
StarlingX syslog-ng configuration file

%prep

%setup

%build

%install
install -d %{buildroot}%{_datadir}/starlingx
install -D -m644 syslog-ng.conf %{buildroot}%{_datadir}/starlingx/syslog-ng.conf
install -D -m644 syslog-ng.logrotate %{buildroot}%{_datadir}/starlingx/syslog-ng.logrotate
install -D -m644 remotelogging.conf %{buildroot}%{_sysconfdir}/syslog-ng/remotelogging.conf
install -d %{buildroot}%{_sbindir}
install -D -m700 fm_event_syslogger %{buildroot}%{_sbindir}/fm_event_syslogger
install -D -m644 syslog-ng.service %{buildroot}%{_datadir}/starlingx/syslog-ng.service

%post
if [ $1 -eq 1 ] ; then
	cp -f %{_datadir}/starlingx/syslog-ng.conf %{_sysconfdir}/syslog-ng/syslog-ng.conf
	chmod 644 %{_sysconfdir}/syslog-ng/syslog-ng.conf
	cp -f %{_datadir}/starlingx/syslog-ng.logrotate %{_sysconfdir}/logrotate.d/syslog
	chmod 644 %{_sysconfdir}/logrotate.d/syslog
	cp -f %{_datadir}/starlingx/syslog-ng.service %{_unitdir}/syslog-ng.service
	chmod 644 %{_unitdir}/syslog-ng.service
fi
ldconfig
%systemd_post syslog-ng.service

%preun
%systemd_preun syslog-ng.service

%postun
ldconfig
%systemd_postun_with_restart syslog-ng.service


%files
%defattr(-,root,root)
%license LICENSE
%config(noreplace) %{_sysconfdir}/syslog-ng/remotelogging.conf
%{_datadir}/starlingx/syslog-ng.conf
%{_datadir}/starlingx/syslog-ng.logrotate
%{_datadir}/starlingx/syslog-ng.service
%{_sbindir}/fm_event_syslogger
