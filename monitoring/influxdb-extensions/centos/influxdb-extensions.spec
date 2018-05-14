Summary: Titanuim Server influxdb Extensions Package
Name: influxdb-extensions
Version: 1.0
Release: 0%{?_tis_dist}.%{tis_patch_ver}
License: windriver
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown

# create the files tarball
Source0: %{name}-%{version}.tar.gz

source1: influxdb.service
Source2: influxdb.conf.pmon

Requires: systemd
Requires: influxdb
Requires: /bin/systemctl

%description
Titanium Cloud influxdb extensions

%define debug_package %{nil}
%define local_unit_dir %{_sysconfdir}/systemd/system

%prep
%setup

%build

%install
install -m 755 -d %{buildroot}%{_sysconfdir}
install -m 755 -d %{buildroot}%{_sysconfdir}/influxdb
install -m 755 -d %{buildroot}%{local_unit_dir}

install -m 644 %{SOURCE1} %{buildroot}%{local_unit_dir}
install -m 600 %{SOURCE2} %{buildroot}%{_sysconfdir}/influxdb


%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%config(noreplace) %{local_unit_dir}/influxdb.service
%{_sysconfdir}/influxdb/*
