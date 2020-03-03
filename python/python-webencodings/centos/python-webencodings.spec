%global __python2 %__python
%global python2_sitelib %python_sitelib

Name:           python-webencodings
Version:        0.5.1
Release:        1.el7%{?_tis_dist}.%{tis_patch_ver}
Summary:        This is a Python implementation of the WHATWG Encoding standard.

Group:          Applications/System
License:        (Python or ZPLv2.0) and ASL 2.0
URL:            https://github.com/gsnedders/python-webencodings/archive/v0.5.1.tar.gz
Source0:        python-webencodings-0.5.1.tar.gz

BuildArch:      noarch

%description
This is a Python implementation of the WHATWG Encoding standard.

%package -n python2-webencodings
Summary:        This is a Python implementation of the WHATWG Encoding standard.
%{?python_provide:%python_provide python2-webencodings}
%description -n python2-webencodings
This is a Python implementation of the WHATWG Encoding standard.

%prep
%setup

%build
export PBR_VERSION=%{version}
%{__python} setup.py build

%install
%{__python2} setup.py install --skip-build --root %{buildroot}

# Don't ship these
# rm -r docs/{conf.py}

%files -n python2-webencodings
# %doc docs/*
%{python2_sitelib}/*

%changelog

