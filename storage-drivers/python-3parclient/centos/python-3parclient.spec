%define name python3-3parclient
%define version 4.2.3
Summary: HPE 3PAR HTTP REST Client
Name: %{name}
Version: %{version}
Release: 0%{?_tis_dist}.%{tis_patch_ver}
Source0: %{name}-%{version}.tar.gz
License: Apache License, Version 2.0
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Walter A. Boring IV <walter.boring@hpe.com>
Url: http://packages.python.org/python-3parclient

BuildRequires:    python3-devel
BuildRequires:    python3-setuptools
BuildRequires:    python3-pip
BuildRequires:    python3-wheel

%description
HPE 3PAR HTTP REST Client

%prep
%setup -q

%build
%{__python3} setup.py build
%py3_build_wheel

%install
%{__python3} setup.py install -O1 --skip-build --root %{buildroot} --record=INSTALLED_FILES
mkdir -p $RPM_BUILD_ROOT/wheels
install -m 644 dist/*.whl $RPM_BUILD_ROOT/wheels/

%clean
rm -rf %{buildroot}

%files -f INSTALLED_FILES
%defattr(-,root,root)

%package wheels
Summary: %{name} wheels

%description wheels
Contains python wheels for %{name}

%files wheels
/wheels/*
