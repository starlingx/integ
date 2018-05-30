%define _CC gcc

Summary: namespace utils
Name: namespace-utils
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown
Source0: %{name}-%{version}.tar.gz

%description
Titanium Cloud namespace utilities

%prep
%setup -q

%build
%{_CC} -o bashns bashns.c

%install
rm -rf ${RPM_BUILD_ROOT}
install -d -m 755 ${RPM_BUILD_ROOT}%{_sbindir}
install -m 500 bashns ${RPM_BUILD_ROOT}%{_sbindir}
install -m 500 umount-in-namespace ${RPM_BUILD_ROOT}%{_sbindir}

%clean
rm -rf ${RPM_BUILD_ROOT}

%files
%license LICENSE
%defattr(-,root,root,-)
%{_sbindir}/umount-in-namespace
%{_sbindir}/bashns
