%{!?_licensedir:%global license %%doc}
%global pypi_name python-cephclient

Name:      python-cephclient
Version:   0.1.0.5
Release:   0%{?_tis_dist}.%{tis_patch_ver}
Summary:   python-cephclient

License:   Apache-2.0
URL:       https://github.com/dmsimard/python-cephclient
Group:     devel/python
Packager:  Wind River <info@windriver.com>

Source0:   %{pypi_name}-v%{version}.tar.gz

Patch0:    fix-osd-crush-remove.patch
Patch1:    set-default-endpoint.patch
Patch2:    0001-US63903-Ceph-Rebase-Update-REST-API-to-0.94.2.patch
Patch3:    add-osd-get-pool-quota.patch
Patch4:    0001-US70398-Ceph-Rebase-Update-REST-API-to-0.94.5.patch
Patch5:    fix-osd-tier-add.patch
Patch6:    US92424-Ceph-Rebase-Update-REST-API-to-10.2.4.patch

BuildArch: noarch

BuildRequires: python
BuildRequires: ceph
BuildRequires: python2-pip
BuildRequires: python2-wheel

Requires: python

Provides: python-cephclient

%description
Client library for the Ceph REST API

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
%doc README.rst
%license LICENSE
%{python2_sitelib}/cephclient
%{python2_sitelib}/*.egg-info

%package wheels
Summary: %{name} wheels

%description wheels
Contains python wheels for %{name}

%files wheels
/wheels/*
