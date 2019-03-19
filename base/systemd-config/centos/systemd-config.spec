#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#
Summary: StarlingX systemd Configuration File
Name: systemd-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: config-files
Packager: StarlingX
URL: unknown
Source: %name-%version.tar.gz

BuildArch: noarch
BuildRequires: systemd = 219-62.el7
Requires: systemd

%define debug_package %{nil}

%description
StarlingX systemd configuration file

%prep

%setup

%build

%install
install -d %{buildroot}%{_datadir}/starlingx
install -m644 60-persistent-storage.rules %{buildroot}%{_datadir}/starlingx/60-persistent-storage.rules
install -m644 journald.conf %{buildroot}%{_datadir}/starlingx/journald.conf
install -m644 systemd.conf.tmpfiles.d %{buildroot}%{_datadir}/starlingx/systemd.conf.tmpfiles.d
install -m644 tmp.conf.tmpfiles.d %{buildroot}%{_datadir}/starlingx/tmp.conf.tmpfiles.d
install -m644 tmp.mount %{buildroot}%{_datadir}/starlingx/tmp.mount

%post
if [ $1 -eq 1 ] ; then
    cp -f %{_datadir}/starlingx/60-persistent-storage.rules %{_udevrulesdir}/
    chmod 644 %{_udevrulesdir}/60-persistent-storage.rules
    cp -f %{_datadir}/starlingx/journald.conf %{_sysconfdir}/systemd
    chmod 644 %{_sysconfdir}/systemd/journald.conf
    cp -f %{_datadir}/starlingx/systemd.conf.tmpfiles.d %{_usr}/lib/tmpfiles.d/systemd.conf
    chmod 644 %{_usr}/lib/tmpfiles.d/systemd.conf
    cp -f %{_datadir}/starlingx/tmp.conf.tmpfiles.d %{_usr}/lib/tmpfiles.d/tmp.conf
    chmod 644 %{_usr}/lib/tmpfiles.d/tmp.conf
    cp -f %{_datadir}/starlingx/tmp.mount %{_unitdir}/
    chmod 644 %{_unitdir}/tmp.mount
fi

%files
%defattr(-,root,root)
%license LICENSE
%{_datadir}/starlingx/60-persistent-storage.rules
%{_datadir}/starlingx/journald.conf
%{_datadir}/starlingx/systemd.conf.tmpfiles.d
%{_datadir}/starlingx/tmp.conf.tmpfiles.d
%{_datadir}/starlingx/tmp.mount
