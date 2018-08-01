Summary: File System Script Package
Name: filesystem-scripts
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown
Source0: %{name}-%{version}.tar.gz
Source1: LICENSE

BuildRequires: systemd-devel
Requires: /bin/systemctl

%description
File System Script Package

%define local_bindir /usr/bin/
%define local_etc_initd /etc/init.d/
%define local_ocfdir /usr/lib/ocf/resource.d/platform/

%define debug_package %{nil}

%prep
%setup

%build

%install

install -d -m 755 %{buildroot}%{local_etc_initd}
install -p -D -m 755 uexportfs %{buildroot}%{local_etc_initd}/uexportfs

install -d -m 755 %{buildroot}%{local_ocfdir}
install -p -D -m 755 nfsserver-mgmt %{buildroot}%{local_ocfdir}/nfsserver-mgmt

install -d -m 755 %{buildroot}%{local_bindir}
install -p -D -m 755 nfs-mount %{buildroot}%{local_bindir}/nfs-mount

install -p -D -m 644 uexportfs.service %{buildroot}%{_unitdir}/uexportfs.service

%post
/bin/systemctl enable uexportfs.service


%clean
rm -rf $RPM_BUILD_ROOT

%files
%license LICENSE
%defattr(-,root,root,-)
%{local_bindir}/*
%{local_etc_initd}/*
%dir %{local_ocfdir}
%{local_ocfdir}/*
%{_unitdir}/uexportfs.service
