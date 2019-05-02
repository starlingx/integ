Summary: Handle Ceph API calls and provide status updates via alarms
Name: python-cephclient
Version: 13.2.2.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: https://github.com/openstack/stx-integ/tree/master/ceph/python-cephclient/python-cephclient'
Source0: %{name}-%{version}.tar.gz

BuildArch: noarch

BuildRequires: python
BuildRequires: python2-pip
BuildRequires: python2-wheel

Requires: python
Requires: python-ipaddress
Requires: python2-six
Requires: python2-requests

Provides: python-cephclient

%description
A client library in Python for Ceph Mgr RESTful plugin providing REST API
access to the cluster over an SSL-secured connection. Python API is compatible
with the old Python Ceph client at
https://github.com/dmsimard/python-cephclient that no longer works in Ceph
mimic because Ceph REST API component was removed.

%define debug_package %{nil}

%prep
%autosetup -p 1 -n %{name}-%{version}

rm -rf .pytest_cache
rm -rf python_cephclient.egg-info
rm -f requirements.txt

%build
%{__python} setup.py build
%py2_build_wheel

%install
%{__python2} setup.py install --skip-build --root %{buildroot}
mkdir -p $RPM_BUILD_ROOT/wheels
install -m 644 dist/*.whl $RPM_BUILD_ROOT/wheels/

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%license LICENSE
%{python2_sitelib}/cephclient
%{python2_sitelib}/*.egg-info

%package wheels
Summary: %{name} wheels

%description wheels
Contains python wheels for %{name}

%files wheels
/wheels/*
