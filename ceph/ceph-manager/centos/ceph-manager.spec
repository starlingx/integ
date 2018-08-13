Summary: Handle Ceph API calls and provide status updates via alarms
Name: ceph-manager
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown
Source0: %{name}-%{version}.tar.gz

BuildRequires: python-setuptools
BuildRequires: systemd-units
BuildRequires: systemd-devel
Requires: sysinv

%description
Handle Ceph API calls and provide status updates via alarms.
Handle sysinv RPC calls for long running Ceph API operations:
- cache tiering enable
- cache tiering disable 

%define local_bindir /usr/bin/
%define local_etc_initd /etc/init.d/
%define local_etc_logrotated /etc/logrotate.d/
%define pythonroot /usr/lib64/python2.7/site-packages

%define debug_package %{nil}

%prep
%setup

%build
%{__python} setup.py build

%install
%{__python} setup.py install --root=$RPM_BUILD_ROOT \
                             --install-lib=%{pythonroot} \
                             --prefix=/usr \
                             --install-data=/usr/share \
                             --single-version-externally-managed

install -d -m 755 %{buildroot}%{local_etc_initd}
install -p -D -m 700 scripts/init.d/ceph-manager %{buildroot}%{local_etc_initd}/ceph-manager

install -d -m 755 %{buildroot}%{local_bindir}
install -p -D -m 700 scripts/bin/ceph-manager %{buildroot}%{local_bindir}/ceph-manager

install -d -m 755 %{buildroot}%{local_etc_logrotated}
install -p -D -m 644 files/ceph-manager.logrotate %{buildroot}%{local_etc_logrotated}/ceph-manager.logrotate

install -d -m 755 %{buildroot}%{_unitdir}
install -m 644 -p -D files/%{name}.service %{buildroot}%{_unitdir}/%{name}.service

%clean
rm -rf $RPM_BUILD_ROOT 

# Note: The package name is ceph-manager but the import name is ceph_manager so
# can't use '%{name}'.
%files
%defattr(-,root,root,-)
%doc LICENSE
%{local_bindir}/*
%{local_etc_initd}/*
%{_unitdir}/%{name}.service
%dir %{local_etc_logrotated}
%{local_etc_logrotated}/*
%dir %{pythonroot}/ceph_manager
%{pythonroot}/ceph_manager/*
%dir %{pythonroot}/ceph_manager-%{version}.0-py2.7.egg-info
%{pythonroot}/ceph_manager-%{version}.0-py2.7.egg-info/*
