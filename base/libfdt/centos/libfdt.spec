Summary: libfdt
Name: libfdt
Version: 1.4.4
Release: 0%{?_tis_dist}.%{tis_patch_ver}
License: GPLv2
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown
Source0: dtc-1.4.4.tar.gz

BuildRequires: gcc
BuildRequires: bison
BuildRequires: flex

%define debug_package %{nil}

%description
Device Tree Compiler

%package -n libfdt-devel
Summary: libfdt devel

%description -n libfdt-devel
libfdt devel

%define prefix /usr/

%prep
%setup -n dtc-1.4.4

%build
make

%install
make install PREFIX=%{buildroot}%{prefix}

%clean
rm -rf $RPM_BUILD_ROOT

%files
%license GPL README.license
%defattr(-,root,root,-)

# TODO: Devel shouldn't contain bin
%files -n libfdt-devel
%license GPL README.license
%defattr(-,root,root,-)
%{prefix}/bin/*
%dir %{prefix}/include
%{prefix}/include/*
%{prefix}/lib/*
