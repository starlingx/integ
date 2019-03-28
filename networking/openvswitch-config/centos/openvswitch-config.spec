#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#
Summary: StarlingX openvswitch Configuration File
Name: openvswitch-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: config-files
Packager: StarlingX
URL: unknown
Source: %name-%version.tar.gz

BuildArch: noarch
Requires: openvswitch

%define debug_package %{nil}

%description
StarlingX openvswitch configuration file

%prep

%setup

%build

%install
install -d -m 0755 %{buildroot}%{_sysconfdir}/openvswitch
install -m 0644 ovsdb-server.pmon.conf %{buildroot}%{_sysconfdir}/openvswitch/ovsdb-server.pmon.conf
install -m 0644 ovs-vswitchd.pmon.conf %{buildroot}%{_sysconfdir}/openvswitch/ovs-vswitchd.pmon.conf
install -d %{buildroot}%{_datadir}/starlingx
install -m 0640 etc_logrotate.d_openvswitch %{buildroot}%{_datadir}/starlingx/etc_logrotate.d_openvswitch

%post
if [ $1 -eq 1 ] ; then
    cp -f %{_datadir}/starlingx/etc_logrotate.d_openvswitch %{_sysconfdir}/logrotate.d/openvswitch
    chmod 644 %{_sysconfdir}/logrotate.d/openvswitch
fi

%files
%defattr(-,root,root)
%license LICENSE
%config(noreplace) %{_sysconfdir}/openvswitch/ovsdb-server.pmon.conf
%config(noreplace) %{_sysconfdir}/openvswitch/ovs-vswitchd.pmon.conf
%{_datadir}/starlingx/etc_logrotate.d_openvswitch
