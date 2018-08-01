Summary: Management of /var/log filesystem
Name: logmgmt
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown
Source0: %{name}-%{version}.tar.gz
Source1: LICENSE

BuildRequires: python-setuptools
BuildRequires: systemd-devel
Requires: systemd
Requires: python-daemon

%description
Management of /var/log filesystem

%define local_bindir /usr/bin/
%define local_etc_initd /etc/init.d/
%define local_etc_pmond /etc/pmon.d/
%define pythonroot /usr/lib64/python2.7/site-packages

%define debug_package %{nil}

%prep
%setup

# Remove bundled egg-info
rm -rf *.egg-info

%build
%{__python} setup.py build

%install
%{__python} setup.py install --root=$RPM_BUILD_ROOT \
                             --install-lib=%{pythonroot} \
                             --prefix=/usr \
                             --install-data=/usr/share \
                             --single-version-externally-managed

install -d -m 755 %{buildroot}%{local_bindir}
install -p -D -m 700 scripts/bin/logmgmt %{buildroot}%{local_bindir}/logmgmt
install -p -D -m 700 scripts/bin/logmgmt_postrotate %{buildroot}%{local_bindir}/logmgmt_postrotate
install -p -D -m 700 scripts/bin/logmgmt_prerotate %{buildroot}%{local_bindir}/logmgmt_prerotate

install -d -m 755 %{buildroot}%{local_etc_initd}
install -p -D -m 700 scripts/init.d/logmgmt %{buildroot}%{local_etc_initd}/logmgmt

install -d -m 755 %{buildroot}%{local_etc_pmond}
install -p -D -m 644 scripts/pmon.d/logmgmt %{buildroot}%{local_etc_pmond}/logmgmt

install -p -D -m 664 scripts/etc/systemd/system/logmgmt.service %{buildroot}%{_unitdir}/logmgmt.service

%post
/usr/bin/systemctl enable logmgmt.service >/dev/null 2>&1

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc LICENSE
%{local_bindir}/*
%{local_etc_initd}/*
%dir %{local_etc_pmond}
%{local_etc_pmond}/*
%{_unitdir}/logmgmt.service
%dir %{pythonroot}/%{name}
%{pythonroot}/%{name}/*
%dir %{pythonroot}/%{name}-%{version}.0-py2.7.egg-info
%{pythonroot}/%{name}-%{version}.0-py2.7.egg-info/*
