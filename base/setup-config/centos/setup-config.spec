#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#
Summary: setup-config
Name: setup-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Requires: setup
Summary: package StarlingX configuration files of setup to system folder.

%description
package StarlingX configuration files of setup to system folder.

%prep
%setup

%build

%install
%{__install} -d  %{buildroot}%{_sysconfdir}/profile.d
%{__install} -d  %{buildroot}%{_datadir}/starlingx
%{__install} -m 644 motd          %{buildroot}%{_datadir}/starlingx/stx.motd
%{__install} -m 644 prompt.sh     %{buildroot}%{_sysconfdir}/profile.d/prompt.sh
%{__install} -m 644 custom.sh     %{buildroot}%{_sysconfdir}/profile.d/custom.sh

%post
if [ $1 -eq 1 ] ; then
        # Initial installation
        cp -f %{_datadir}/starlingx/stx.motd    %{_sysconfdir}/motd
        chmod 600   %{_sysconfdir}/{exports,fstab}
fi

%files
%defattr(-,root,root,-)
%{_datadir}/starlingx/stx.motd
%{_sysconfdir}/profile.d/prompt.sh
%{_sysconfdir}/profile.d/custom.sh
