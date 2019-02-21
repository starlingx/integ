Summary: StarlingX Docker Configuration File
Name: docker-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: config-files
Packager: StarlingX
URL: unknown

Source0: %{name}-%{version}.tar.gz

BuildArch: noarch
Requires: docker-ce

%define debug_package %{nil}

%description
StarlingX docker configuration file

%prep
%setup

%install
make DATADIR=%{buildroot}%{_datadir} SYSCONFDIR=%{buildroot}%{_sysconfdir} install

%files
%defattr(-,root,root)
%license LICENSE
%dir %{_sysconfdir}/systemd/system/docker.service.d
%{_sysconfdir}/pmon.d/docker.conf
%{_sysconfdir}/systemd/system/docker.service.d/docker-stx-override.conf
