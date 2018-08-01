Summary: build-info version 1.0-r3
Name: build-info
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown
Source0: %{name}-%{version}.tar.gz
Source1: LICENSE

%description
Build Info

%define local_etcdir /etc
%define local_incdir /usr/include

%define debug_package %{nil}

%package -n build-info-dev
Summary: build-info version 1.0-r3 - Development files
Group: devel

%description -n build-info-dev
Build Info  This package contains symbolic links, header files, and related items necessary for software development.

%files
%license ../LICENSE
%defattr(-,root,root,-)
%{local_etcdir}/*

%prep
%setup

%build
./collect.sh

%install
install -d -m 755 %{buildroot}%{local_etcdir}
install -m 644 build.info %{buildroot}/%{local_etcdir}
install -d -m 755 %{buildroot}%{local_incdir}
install -m 644 build_info.h %{buildroot}/%{local_incdir}

%clean
rm -rf $RPM_BUILD_ROOT

%files -n build-info-dev
%defattr(-,root,root,-)
%{local_incdir}/*

