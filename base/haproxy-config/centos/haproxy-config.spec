#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#
Summary: haproxy-config
Name: haproxy-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Requires: haproxy
Summary: package StarlingX configuration files of haproxy to system folder.

%description
package StarlingX configuration files of haproxy to system folder.

%prep
%setup

%build

%install
%{__install} -d 755 %{buildroot}%{_sysconfdir}/haproxy/errors/
%{__install} -m 755 503.http %{buildroot}%{_sysconfdir}/haproxy/errors/503.http

%{__install} -d  %{buildroot}%{_sysconfdir}/systemd/system
%{__install} -m 644 haproxy.service %{buildroot}%{_sysconfdir}/systemd/system

mkdir -p %{_sysconfdir}/init.d
%{__install} -p -D -m 0755 haproxy.sh %{buildroot}%{_sysconfdir}/init.d/haproxy

%post
/bin/systemctl disable haproxy.service
if test -s %{_sysconfdir}/logrotate.d/haproxy ; then
    echo '#See /etc/logrotate.d/syslog for haproxy rules' > %{_sysconfdir}/logrotate.d/haproxy
fi

%files
%defattr(-,root,root,-)
%dir %{_sysconfdir}/haproxy/errors/
%{_sysconfdir}/haproxy/errors/*
%{_sysconfdir}/init.d/haproxy
%{_sysconfdir}/systemd/system/haproxy.service
