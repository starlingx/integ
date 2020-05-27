# Dependencies for check and wheel introduce circular dependencies
# Set this to 0 after we've bootstrapped.

%global with_check 0
%global build_wheel 0

# define some macros for RHEL 6
%global __python2 %__python
%global python2_sitelib %python_sitelib

Name:           mechanize
Version:        0.4.5
Release:        1.el7%{?_tis_dist}.%{tis_patch_ver}
Summary:        Automate interaction with HTTP web servers

Group:          Applications/System
License:        (Python or ZPLv2.0) and ASL 2.0
URL:            https://github.com/python-mechanize/mechanize
Source0:        mechanize-0.4.5.tar.gz

BuildArch:      noarch
%if 0%{?with_python3}
BuildRequires:  python3-devel
BuildRequires:  python3-pip
BuildRequires:  python3-wheel
Requires:       python3-html5lib
%else
BuildRequires:  python2-devel
BuildRequires:  python-pip
BuildRequires:  python-wheel
Requires:       python-html5lib
%endif


%description
Stateful programmatic web browsing in Python.

%package -n python2-mechanize
Summary:        Automate interaction with HTTP web servers
%{?python_provide:%python_provide python2-mechanize}
%description -n python2-mechanize
Stateful programmatic web browsing in Python.

%if 0%{?with_python3}
%package -n python3-mechanize
Summary:        Automate interaction with HTTP web servers
Group:          Applications/System
%{?python_provide:%python_provide python3-mechanize}

%description -n python3-mechanize
Stateful programmatic web browsing in Python.

%endif # with_python3

%prep
%setup

%build
export PBR_VERSION=%{version}
%{__python} setup.py build

%if 0%{?with_python3}
%{__python3} setup.py build
%endif # with_python3

%install
# Must do the python3 install first because the scripts in /usr/bin are
# overwritten with every setup.py install (and we want the python2 version
# to be the default for now).
%if 0%{?with_python3}
%if 0%{?build_wheel}
pip3 install -I dist/%{python3_wheelname} --root %{buildroot} --strip-file-prefix %{buildroot}
%else
%{__python3} setup.py install --skip-build --root %{buildroot}
%endif

rm -rf %{buildroot}%{python3_sitelib}/mechanize/test
rm -rf %{buildroot}%{python3_sitelib}/mechanize/test-tools
rm -rf %{buildroot}%{python3_sitelib}/mechanize/run_tests.py
%if 0%{?build_wheel}
sed -i '/^mechanize\/tests\//d' %{buildroot}%{python3_record}
%endif

find %{buildroot}%{python3_sitelib} -name '*.exe' | xargs rm -f
%endif # with_python3

%if 0%{?build_wheel}
pip2 install -I dist/%{python2_wheelname} --root %{buildroot} --strip-file-prefix %{buildroot}
%else
%{__python2} setup.py install --skip-build --root %{buildroot}
%endif

rm -rf %{buildroot}%{python2_sitelib}/mechanize/test
rm -rf %{buildroot}%{python2_sitelib}/mechanize/test-tools
rm -rf %{buildroot}%{python2_sitelib}/mechanize/run_tests.py
%if 0%{?build_wheel}
sed -i '/^mechanize\/tests\//d' %{buildroot}%{python2_record}
%endif

find %{buildroot}%{python2_sitelib} -name '*.exe' | xargs rm -f

# Don't ship these
rm -r docs/{Makefile,conf.py}

%if 0%{?with_check}
%check
LANG=en_US.utf8 PYTHONPATH=$(pwd) py.test

%if 0%{?with_python3}
LANG=en_US.utf8 PYTHONPATH=$(pwd) py.test-%{python3_version}
%endif # with_python3
%endif # with_check

%files -n python2-mechanize
%doc docs/*
%{python2_sitelib}/*

%if 0%{?with_python3}
%files -n python3-mechanize
%doc docs/*
%{python3_sitelib}/mechanize*/
%endif # with_python3

%changelog

