# Where dhcp configuration files are stored
%global dhcpconfdir %{_sysconfdir}/dhcp

Summary: dhcp-config
Name: dhcp-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Requires: dhclient
Summary: package StarlingX configuration files of dhcp to system folder.

%description
package StarlingX configuration files of dhcp to system folder.

%prep
%setup

%build

%install
%{__install} -d %{buildroot}%{dhcpconfdir}
%{__install} -p -m 0755 dhclient-enter-hooks %{buildroot}%{dhcpconfdir}/dhclient-enter-hooks
%{__install} -p -m 0644 dhclient.conf %{buildroot}%{dhcpconfdir}/dhclient.conf

%post

%files
%config(noreplace) %{dhcpconfdir}/dhclient.conf
%{dhcpconfdir}/dhclient-enter-hooks

