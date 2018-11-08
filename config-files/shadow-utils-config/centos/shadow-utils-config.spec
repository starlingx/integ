Summary: StarlingX shadow-utils Configuration File
Name: shadow-utils-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: config-files
Packager: StarlingX
URL: unknown

Source0: LICENSE
Source1: login.defs
Source2: clear_shadow_locks.service

BuildArch: noarch
# systemd provides %{_unitdir}
BuildRequires: systemd
Requires: setup
Requires: shadow-utils

%define debug_package %{nil}

%description
StarlingX shadow-utils configuration file

%install
install -d %{buildroot}%{_sysconfdir}
install -d %{buildroot}%{_datadir}/starlingx
install -D -m644 %{SOURCE1} %{buildroot}%{_datadir}/starlingx/login.defs

install -d -m 755 %{buildroot}%{_sysconfdir}/init.d
install -D -m644 %{SOURCE2} %{buildroot}%{_unitdir}/clear_shadow_locks.service

%post
if [ $1 -eq 1 ] ; then
	cp -f %{_datadir}/starlingx/login.defs %{_sysconfdir}/
	chmod 644 %{_sysconfdir}/login.defs
fi
%systemd_post clear_shadow_locks.service

%preun
%systemd_preun clear_shadow_locks.service

%postun
%systemd_postun_with_restart clear_shadow_locks.service

%files
%defattr(-,root,root)
%license ../SOURCES/LICENSE
%{_unitdir}/clear_shadow_locks.service
%{_datadir}/starlingx/login.defs
