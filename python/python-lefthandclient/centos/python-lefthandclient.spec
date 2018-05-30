%define name python-lefthandclient
%define version 2.1.0
%define release 1

Summary: HPE LeftHand/StoreVirtual HTTP REST Client
Name: %{name}
Version: %{version}
Release: 0%{?_tis_dist}.%{tis_patch_ver}
Source0: %{name}-%{version}.tar.gz
License: Apache License, Version 2.0
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Kurt Martin <kurt.f.martin@hpe.com>
Url: http://packages.python.org/python-lefthandclient

BuildRequires:    python2-devel
BuildRequires:    python-setuptools

%description
HPE LeftHand/StoreVirtual HTTP REST Client

%prep
%setup -q

%build
%{__python2} setup.py build

%install
%{__python2} setup.py install -O1 --skip-build --root %{buildroot} --record=INSTALLED_FILES

%clean
rm -rf %{buildroot}

%files -f INSTALLED_FILES
%defattr(-,root,root)
