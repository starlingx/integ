Summary: A utility belt for advanced users of python-requests
Name: requests-toolbelt
Version: 0.5.1
Release: 0%{?_tis_dist}.%{tis_patch_ver}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: https://toolbelt.readthedocs.org/
Source0: %{name}-%{version}.tar.gz

%define debug_package %{nil}

BuildRequires: python-setuptools
Requires: python-devel
Requires: /bin/bash

%description
A utility belt for advanced users of python-requests

%define pythonroot           /usr/lib64/python2.7/site-packages

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

%clean
rm -rf $RPM_BUILD_ROOT 

%files
%defattr(-,root,root,-)
%doc LICENSE
%{pythonroot}/requests_toolbelt
%{pythonroot}/requests_toolbelt-*.egg-info

