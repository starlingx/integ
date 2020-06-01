# define some macros for RHEL 6
%global __python2 %__python
%global python2_sitelib %python_sitelib

Name:           html5lib-python
Version:        1.0.1
Release:        1.el7%{?_tis_dist}.%{tis_patch_ver}
Summary:        Python library for parsing HTML

Group:          Applications/System
License:        MIT License
URL:            https://github.com/html5lib/html5lib-python/archive/1.0.1.tar.gz
Source0:        html5lib-python-1.0.1.tar.gz

BuildArch:      noarch

%if 0%{?with_python3}
BuildRequires:  python3-devel
BuildRequires:  python3-pip
BuildRequires:  python3-wheel
Requires:       python3-webencodings
%else
BuildRequires:  python2-devel
BuildRequires:  python-pip
BuildRequires:  python-wheel
Requires:       python-webencodings
%endif


%description
Python library for parsing HTML

%package -n python2-html5lib
Summary:        Python library for parsing HTML
%{?python_provide:%python_provide python2-html5lib}
%description -n python2-html5lib
Python library for parsing HTML

%if 0%{?with_python3}
%package -n python3-html5lib
Summary:        Python library for parsing HTML
Group:          Applications/System
%{?python_provide:%python_provide python3-html5lib}

%description -n python3-html5lib
Python library for parsing HTML

%endif # with_python3

%prep
%setup  -q -n html5lib-%{version}


%build
export PBR_VERSION=%{version}
%{__python} setup.py build
%py2_build_wheel

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

sed -i '/\/usr\/bin\/easy_install,/d' %{buildroot}%{python3_record}
%else
%{__python3} setup.py install --skip-build --root %{buildroot}
%endif

find %{buildroot}%{python3_sitelib} -name '*.exe' | xargs rm -f
%endif # with_python3

%if 0%{?build_wheel}
pip2 install -I dist/%{python2_wheelname} --root %{buildroot} --strip-file-prefix %{buildroot}
%else
%{__python2} setup.py install --skip-build --root %{buildroot}
%endif

find %{buildroot}%{python2_sitelib} -name '*.exe' | xargs rm -f

# Don't ship these
# rm -r docs/{Makefile,conf.py}

%if 0%{?with_check}
%check
LANG=en_US.utf8 PYTHONPATH=$(pwd) py.test

%if 0%{?with_python3}
LANG=en_US.utf8 PYTHONPATH=$(pwd) py.test-%{python3_version}
%endif # with_python3
%endif # with_check

%files -n python2-html5lib
# %doc docs/*
%{python2_sitelib}/*

%if 0%{?with_python3}
%files -n python3-html5lib
# %doc docs/*
%{python3_sitelib}/html5lib*/
%endif # with_python3

%changelog

