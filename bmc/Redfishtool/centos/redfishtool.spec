#
# SPDX-License-Identifier: BSD-3-Clause
#
# Copyright (c) 2016, Contributing Member(s) of Distributed Management
# Task Force, Inc.. All rights reserved.

Summary: Redfish Tool Package
Name: Redfishtool
Version: 1.1.0
Release: %{?_tis_dist}.%{tis_patch_ver}
#For full text see link: https://github.com/DMTF/Redfishtool/blob/master/LICENSE.md
License: BSD-3-Clause.
Group: base
Packager: StarlingX
URL: https://github.com/DMTF/Redfishtool

Source0: %{name}-%{version}.tar.gz

BuildArch: noarch

Patch01: 0001-Adapt-redfishtool-to-python2.patch

BuildRequires: python-setuptools

Requires:      python-requests

%description
Redfish Tool Package

%define pythonroot           /usr/lib64/python2.7/site-packages
%define debug_package %{nil}

%prep
%setup
%patch01 -p1

# Remove bundled egg-info
rm -rf *.egg-info

%build
%{__python} setup.py build

%install
%{__python} setup.py install --root=%{buildroot} \
                             --install-lib=%{pythonroot} \
                             --prefix=/usr \
                             --install-data=/usr/share \
                             --single-version-externally-managed

%post

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc LICENSE.md
%{pythonroot}/redfishtool/*
%{pythonroot}/redfishtool-%{version}*.egg-info

%{_bindir}/redfishtool
