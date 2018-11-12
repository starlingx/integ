Summary: dnsmasq-config
Name: dnsmasq-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Requires: dnsmasq
Summary: package StarlingX configuration files of dnsmasq to system folder.

%description
package StarlingX configuration files of dnsmasq to system folder.

%prep
%setup

%build

%install
mkdir -p %{buildroot}%{_sysconfdir}/init.d
install -m 755 init  %{buildroot}%{_sysconfdir}/init.d/dnsmasq

%post

%files
%{_sysconfdir}/init.d/dnsmasq
