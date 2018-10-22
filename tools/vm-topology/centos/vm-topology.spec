%global pypi_name vm-topology

Summary: vm_topology
Name: vm-topology
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>

URL: unknown
Source0:        %{pypi_name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires: python
BuildRequires: python-setuptools
BuildRequires: python2-pip
BuildRequires: python2-wheel
BuildRequires: python-keyring
BuildRequires: libvirt

Requires: python
Requires: python-keyring
Requires: /usr/bin/env
Requires: libvirt

%description
Show compute resources and VM topology

%prep
%autosetup -p 1 -n %{pypi_name}-%{version}
# Remove bundled egg-info
rm -rf %{pypi_name}.egg-info
# Let RPM handle the dependencies
rm -f requirements.txt

%build
%{__python2} setup.py build
%py2_build_wheel

%install
%{__python2} setup.py install --skip-build --root %{buildroot}
mkdir -p $RPM_BUILD_ROOT/wheels
install -m 644 dist/*.whl $RPM_BUILD_ROOT/wheels/

%files
%defattr(-,root,root,-)
%license LICENSE
%{_bindir}/vm-topology
%{python2_sitelib}/vm_topology
%{python2_sitelib}/*.egg-info

%package wheels
Summary: %{name} wheels

%description wheels
Contains python wheels for %{name}

%files wheels
/wheels/*
