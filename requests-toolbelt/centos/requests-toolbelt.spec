Summary: A utility belt for advanced users of python-requests
Name: requests-toolbelt
Version: 0.9.1
Release: 0%{?_tis_dist}.%{tis_patch_ver}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: https://toolbelt.readthedocs.org/
Source0: %{name}-%{version}.tar.gz

%define debug_package %{nil}

BuildRequires: python3-setuptools
BuildRequires: python3-pip
BuildRequires: python3-wheel
Requires: python3-devel
Requires: /bin/bash

%description
A utility belt for advanced users of python-requests

%define pythonroot           /usr/lib64/python3.6/site-packages/

%prep
%setup

%build
%{__python3} setup.py build
%{__python3} setup.py bdist_wheel

%install
%{__python3} setup.py install --root=$RPM_BUILD_ROOT \
                             --install-lib=%{pythonroot} \
                             --prefix=/usr \
                             --install-data=/usr/share \
                             --single-version-externally-managed
mkdir -p $RPM_BUILD_ROOT/wheels
install -m 644 dist/*.whl $RPM_BUILD_ROOT/wheels/

%clean
rm -rf $RPM_BUILD_ROOT 

%files
%defattr(-,root,root,-)
%doc LICENSE
%{pythonroot}/requests_toolbelt
%{pythonroot}/requests_toolbelt-*.egg-info

%package wheels
Summary: %{name} wheels

%description wheels
Contains python wheels for %{name}

%files wheels
/wheels/*
