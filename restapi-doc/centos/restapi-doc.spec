Summary: RestAPI-Doc
Name: restapi-doc
Version: 1.8.1
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: devel
Packager: Wind River <info@windriver.com>
URL: unknown
BuildRequires: git maven

Source0: %{name}-%{version}.tar.gz
Source1: mvn.repo.tgz

%define cgcs_sdk_deploy_dir /opt/deploy/cgcs_sdk
%define debug_package %{nil}

%description
RestAPI-doc files

%prep
%setup
cp %{SOURCE1} %{_builddir}/%{name}-%{version}

%build
make -j"%(nproc)"

%install
install -D -m 644 wrs-%{name}-%{version}.tgz %{buildroot}%{cgcs_sdk_deploy_dir}/wrs-%{name}-%{version}.tgz

%files
%{cgcs_sdk_deploy_dir}/wrs-%{name}-%{version}.tgz

