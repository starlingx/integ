Summary: memcached-custom
Name: memcached-custom
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Summary: package memcached service files to system folder.

%description
package memcached service files to system folder.

%prep
%setup

%build

%install
%{__install} -d %{buildroot}%{_sysconfdir}/systemd/system
%{__install} -m 644 -p memcached.service %{buildroot}%{_sysconfdir}/systemd/system/memcached.service

%post

%files
%defattr(-,root,root,-)
%{_sysconfdir}/systemd/system/memcached.service

