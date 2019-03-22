#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#
Summary: nfs-utils-config
Name: nfs-utils-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Requires: nfs-utils
Summary: package customized configuration and service files of nfs-utils to system folder.

%description
package customized configuration and service files of nfs-utils to system folder.

%prep
%setup

%build

%install
install -d %{buildroot}%{_sysconfdir}/init.d
install -d %{buildroot}%{_unitdir}
install -d %{buildroot}%{_datadir}/starlingx
install -m 755 -p -D nfscommon %{buildroot}%{_sysconfdir}/init.d
install -m 644 -p -D nfscommon.service %{buildroot}%{_unitdir}
install -m 755 -p -D nfsserver %{buildroot}%{_sysconfdir}/init.d
install -m 644 -p -D nfsserver.service %{buildroot}%{_unitdir}
install -m 644 -p -D nfsmount.conf %{buildroot}%{_datadir}/starlingx/stx.nfsmount.conf

%post
if [ $1 -eq 1 ] ; then
        # Initial installation
        cp -f %{_datadir}/starlingx/stx.nfsmount.conf %{_sysconfdir}/nfsmount.conf
        chmod 644 %{_sysconfdir}/nfsmount.conf
fi
# STX - disable these service files as rpc-statd is started by nfscommon
%{_bindir}/systemctl disable rpc-statd.service
%{_bindir}/systemctl disable rpc-statd-notify.service
%{_bindir}/systemctl disable nfs-lock.service
%{_bindir}/systemctl disable nfslock.service

%{_bindir}/systemctl enable nfscommon.service  >/dev/null 2>&1 || :
%{_bindir}/systemctl enable nfsserver.service  >/dev/null 2>&1 || :

%preun
if [ $1 -eq 0 ]; then
    # pre uninstall
    %{_bindir}/systemctl disable nfscommon.service >/dev/null 2>&1 || :
    %{_bindir}/systemctl disable nfsserver.service >/dev/null 2>&1 || :
fi


%files
%defattr(-,root,root,-)
%{_sysconfdir}/init.d/nfscommon
%{_unitdir}/nfscommon.service
%{_sysconfdir}/init.d/nfsserver
%{_unitdir}/nfsserver.service
%{_datadir}/starlingx/stx.nfsmount.conf
