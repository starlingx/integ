Summary: nova-utils version 1.0-r1
Name: nova-utils
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: development
Packager: Wind River <info@windriver.com>
URL: unknown

Source0: LICENSE
Source1: nova-sriov

%description
Nova utilities package

%package -n nova-utils-devel
Summary: nova-utils - Development files
Group: devel
Requires: nova-utils = %{version}-%{release}

%description -n nova-utils-devel
Nova utilities package  This package contains symbolic links, header files,
and related items necessary for software development.

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/%{_bindir}
install -m 0755 %{SOURCE1} $RPM_BUILD_ROOT/%{_bindir}/nova-sriov
mkdir -p $RPM_BUILD_ROOT/%{_defaultdocdir}/%{name}-%{version}
install -m 644 %{SOURCE0} $RPM_BUILD_ROOT/%{_defaultdocdir}/%{name}-%{version}

%files
%defattr(-,root,root,-)
%{_bindir}/nova-sriov
%{_defaultdocdir}/%{name}-%{version}

%files -n nova-utils-devel
%defattr(-,root,root,-)
