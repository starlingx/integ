%{!?upstream_version: %global upstream_version %{version}%{?milestone}}

%if 0%{?fedora}
%global with_python3 1
%endif

%global pypi_name ryu
%global service neutron

Name:           python-%{pypi_name}
Version:        4.19
Release:        0%{?_tis_dist}.%{tis_patch_ver}
Summary:        Component-based Software-defined Networking Framework

License:        Apache-2.0
Url:            https://osrg.github.io/ryu
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

%description
Ryu provides software components with well defined API that make it easy for developers to create new
network management and control applications.

%package -n     python2-%{pypi_name}
Summary:        Component-based Software-defined Networking Framework
%{?python_provide:%python_provide python2-%{pypi_name}}

Requires:  python-eventlet
Requires:  python-debtcollector
Requires:  python-lxml
Requires:  python-msgpack
Requires:  python-netaddr
#Requires:  python-openvswitch
Requires:  python-oslo-config
Requires:  python-paramiko
Requires:  python-routes
Requires:  python-six
Requires:  python-tinyrpc
Requires:  python-webob
Requires:  python-%{pypi_name}-common = %{version}-%{release}

BuildRequires:  python2-devel
BuildRequires:  python-debtcollector
BuildRequires:  python-eventlet
BuildRequires:  python-greenlet
BuildRequires:  python-lxml
BuildRequires:  python-msgpack
#BuildRequires:  python-openvswitch
BuildRequires:  python-oslo-config
BuildRequires:  python-paramiko
BuildRequires:  python-repoze-lru
BuildRequires:  python-routes
BuildRequires:  python-sphinx
BuildRequires:  python-tinyrpc
BuildRequires:  python-setuptools
BuildRequires:  python-webob

%if 0%{?with_check}
BuildRequires:  pylint
BuildRequires:  python-coverage
BuildRequires:  python-formencode
BuildRequires:  python-nose
BuildRequires:  python-mock
BuildRequires:  python-pep8
BuildRequires:  python-tinyrpc
%endif

%description -n python2-%{pypi_name}
Ryu provides software components with well defined API that make it easy for developers to create new
network management and control applications.

%if 0%{?with_python3}
%package -n     python3-%{pypi_name}
Summary:        Component-based Software-defined Networking Framework
%{?python_provide:%python_provide python3-%{pypi_name}}

Requires:  python3-eventlet
Requires:  python3-debtcollector
Requires:  python3-lxml
Requires:  python3-msgpack
Requires:  python3-netaddr
#Requires:  python3-openvswitch
Requires:  python3-oslo-config
Requires:  python3-paramiko
Requires:  python3-routes
Requires:  python3-six
Requires:  python3-tinyrpc
Requires:  python3-webob
Requires:  python-%{pypi_name}-common = %{version}-%{release}

BuildRequires:  python3-devel
BuildRequires:  python3-debtcollector
BuildRequires:  python3-eventlet
BuildRequires:  python3-greenlet
BuildRequires:  python3-lxml
BuildRequires:  python3-msgpack
#BuildRequires:  python3-openvswitch
BuildRequires:  python3-oslo-config
BuildRequires:  python3-paramiko
BuildRequires:  python3-repoze-lru
BuildRequires:  python3-routes
BuildRequires:  python3-sphinx
BuildRequires:  python3-setuptools
BuildRequires:  python3-tinyrpc
BuildRequires:  python3-webob

%if 0%{?with_check}
BuildRequires:  python3-coverage
BuildRequires:  python3-formencode
BuildRequires:  python3-mock
BuildRequires:  python3-nose
BuildRequires:  python3-pep8
%endif

%description -n python3-%{pypi_name}
Ryu provides software components with well defined API that make it easy for developers to create new
network management and control applications.

This is the Python 3 version.
%endif

%package -n python-%{pypi_name}-common
Summary:        Component-based Software-defined Networking Framework

%description -n python-%{pypi_name}-common
Ryu provides software components with well defined API that make it easy for developers to create new
network management and control applications.

This package contains common data between python 2 and 3 versions

%package -n python-%{pypi_name}-tests
Summary:    Ryu tests
Requires:   python-%{pypi_name} = %{version}-%{release}
%description -n python-%{pypi_name}-tests
Ryu set of tests

%prep
%autosetup -n %{name}-%{upstream_version}
# Remove bundled egg-info
rm -rf %{pypi_name}.egg-info
# drop deps in egginfo, let rpm handle them
rm tools/*-requires
rm tools/install_venv.py
# Remove non-working tests (internet connection needed)
rm -vf %{pypi_name}/tests/unit/test_requirements.py
# Remove pip usage (used only in test_requirements.py)
sed -i '/^from pip/d' ryu/utils.py
# Remove docker based tests (internet connection needed)
rm -rf %{pypi_name}/tests/integrated/bgp
rm -rf %{pypi_name}/tests/integrated/common

%build
export PBR_VERSION=%{version}
%py2_build
%if 0%{?with_python3}
%py3_build
%endif

cd doc && make man

%install
export PBR_VERSION=%{version}
%if 0%{?with_python3}
%py3_install
for bin in %{pypi_name}{,-manager}; do
    mv %{buildroot}%{_bindir}/$bin  %{buildroot}%{_bindir}/$bin-%{python3_version}
    ln -s ./$bin-%{python3_version} %{buildroot}%{_bindir}/$bin-3
done;
%endif
%py2_install
for bin in %{pypi_name}{,-manager}; do
    mv %{buildroot}%{_bindir}/$bin  %{buildroot}%{_bindir}/$bin-%{python2_version}
    ln -s ./$bin-%{python2_version} %{buildroot}%{_bindir}/$bin-2
    ln -s ./$bin-%{python2_version} %{buildroot}%{_bindir}/$bin
done;


install -d -m 755 %{buildroot}%{_sysconfdir}/%{pypi_name}
mv %{buildroot}%{_prefix}%{_sysconfdir}/%{pypi_name}/%{pypi_name}.conf %{buildroot}%{_sysconfdir}/%{pypi_name}/%{pypi_name}.conf

%if 0%{?with_check}
%check
%if 0%{?with_python3}
# Tests without virtualenv (N) and without PEP8 tests (P)
PYTHON=%{__python3} ./run_tests.sh -N -P
%endif
PYTHON=%{__python2} ./run_tests.sh -N -P
%endif

%files -n     python2-%{pypi_name}
%{python2_sitelib}/%{pypi_name}-%{version}-py?.?.egg-info
%{python2_sitelib}/%{pypi_name}
%{_bindir}/%{pypi_name}
%{_bindir}/%{pypi_name}-2
%{_bindir}/%{pypi_name}-%{python2_version}
%{_bindir}/%{pypi_name}-manager
%{_bindir}/%{pypi_name}-manager-2
%{_bindir}/%{pypi_name}-manager-%{python2_version}
%exclude %{python2_sitelib}/%{pypi_name}/tests


%if 0%{?with_python3}
%files -n     python3-%{pypi_name}
%{python3_sitelib}/%{pypi_name}-%{version}-py?.?.egg-info
%{python3_sitelib}/%{pypi_name}
%{_bindir}/%{pypi_name}
%{_bindir}/%{pypi_name}-3
%{_bindir}/%{pypi_name}-%{python3_version}
%{_bindir}/%{pypi_name}-manager
%{_bindir}/%{pypi_name}-manager-3
%{_bindir}/%{pypi_name}-manager-%{python3_version}
%exclude %{python2_sitelib}/%{pypi_name}/tests
%endif

%files -n     python-%{pypi_name}-common
%doc README.rst
%license LICENSE
%dir %attr(0755, root, %{service}) %{_sysconfdir}/%{pypi_name}
%config(noreplace) %attr(0640, root, %{service}) %{_sysconfdir}/%{pypi_name}/%{pypi_name}.conf
%exclude %{python2_sitelib}/%{pypi_name}/tests

%files -n python-%{pypi_name}-tests
%license LICENSE
%{python2_sitelib}/%{pypi_name}/tests

%changelog
* Tue Jul 04 2017 Matt Peters <matt.peters@windriver.com> - 4.15-0
- Upstream 4.15 and Titanium versioning

* Mon May 29 2017 Lumír Balhar <lbalhar@redhat.com> - 4.13-2
- Tests enabled

* Mon May 29 2017 Alan Pevec <alan.pevec@redhat.com> 4.13-1
- Update to 4.13
- Add missing dependencies

* Sat Feb 11 2017 Fedora Release Engineering <releng@fedoraproject.org> - 4.3-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Mon Dec 19 2016 Miro Hrončok <mhroncok@redhat.com> - 4.3-5
- Rebuild for Python 3.6

* Wed Sep 07 2016 Arie Bregman <abregman@redhat.com> - 4.3-4
- Moved tests related lines to depend on with_check

* Tue Jul 19 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 4.3-3
- https://fedoraproject.org/wiki/Changes/Automatic_Provides_for_Python_RPM_Packages

* Fri Jul 01 2016 Matthias Runge <mrunge@redhat.com> - 4.3-2
- add python_provides for python2 package

* Thu Jun 23 2016 Haïkel Guémar <hguemar@fedoraproject.org> - 4.3-1
- Upstream 4.3
- Enable python3 subpackage

* Thu Apr  7 2016 Haïkel Guémar <hguemar@fedoraproject.org> - 3.30-1
- Upstream 3.30

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 3.26-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Sun Nov 22 2015 Arie Bregman <abregman@redhat.com> - 3.26-1
- Initial package.
