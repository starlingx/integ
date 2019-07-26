#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#
Summary: pam-config
Name: pam-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Requires: pam
Requires: openssh
Summary: package StarlingX configuration files of pam to system folder.

%description
package StarlingX configuration files of pam to system folder.

%define _pamconfdir %{_sysconfdir}/pam.d

%prep
%setup

%build

%install
%{__install}  -d  %{buildroot}%{_pamconfdir}
%{__install}  -d  %{buildroot}%{_datadir}/starlingx
%{__install}  -m 644 sshd.pam        %{buildroot}%{_datadir}/starlingx/sshd.pam
%{__install}  -m 644 common-account  %{buildroot}%{_pamconfdir}/common-account
%{__install}  -m 644 common-auth     %{buildroot}%{_pamconfdir}/common-auth
%{__install}  -m 644 common-password %{buildroot}%{_pamconfdir}/common-password
%{__install}  -m 644 common-session  %{buildroot}%{_pamconfdir}/common-session
%{__install}  -m 644 common-session-noninteractive %{buildroot}%{_pamconfdir}/common-session-noninteractive
%{__install}  -m 644 system-auth.pamd %{buildroot}%{_datadir}/starlingx/stx.system-auth

%post
if [ $1 -eq 1 ] ; then
    # Initial installation
    cp -f %{_datadir}/starlingx/stx.system-auth %{_pamconfdir}/system-auth
    cp -f %{_datadir}/starlingx/sshd.pam    %{_pamconfdir}/sshd
fi

%files
%{_datadir}/starlingx/stx.system-auth
%{_datadir}/starlingx/sshd.pam
%config(noreplace) %{_pamconfdir}/common-account
%config(noreplace) %{_pamconfdir}/common-auth
%config(noreplace) %{_pamconfdir}/common-password
%config(noreplace) %{_pamconfdir}/common-session
%config(noreplace) %{_pamconfdir}/common-session-noninteractive
