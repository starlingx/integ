#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#
Summary: util-linux-config
Name: util-linux-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Requires: util-linux
Summary: package StarlingX configuration files of util-linux to system folder.

%description
package StarlingX configuration files of util-linux to system folder.

%prep
%setup

%build

%install
%{__install} -d 644            %{buildroot}%{_datadir}/starlingx/
%{__install} -m 644 stx.su     %{buildroot}%{_datadir}/starlingx/stx.su
%{__install} -m 644 stx.login  %{buildroot}%{_datadir}/starlingx/stx.login

%post
%define _pamconfdir %{_sysconfdir}/pam.d
if [ $1 -eq 1 ] ; then
        cp -f %{_datadir}/starlingx/stx.su     %{_pamconfdir}/su
        cp -f %{_datadir}/starlingx/stx.login  %{_pamconfdir}/login
fi

%preun

%postun

%files
%defattr(-,root,root)
%{_datadir}/starlingx/stx.su
%{_datadir}/starlingx/stx.login
