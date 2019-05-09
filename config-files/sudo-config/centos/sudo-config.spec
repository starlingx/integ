#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#
Summary: StarlingX Sudo Configuration File
Name: sudo-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown

Source0: sysadmin.sudo
Source1: LICENSE

%define SYSADMIN_P 4SuW8cnXFyxsk

%description
StarlingX sudo configuration file

%install
install -d %{buildroot}/%{_sysconfdir}/sudoers.d
install -m 440 %{SOURCE0}  %{buildroot}/%{_sysconfdir}/sudoers.d/sysadmin

%pre
getent group sys_protected >/dev/null || groupadd -f -g 345 sys_protected
getent passwd sysadmin > /dev/null || \
useradd -m -g sys_protected -G root \
    -d /home/sysadmin -p %{SYSADMIN_P} \
    -s /bin/sh sysadmin 2> /dev/null || :

%files
%license ../SOURCES/LICENSE
%config(noreplace) %{_sysconfdir}/sudoers.d/sysadmin
