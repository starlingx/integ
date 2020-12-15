# SPDX-License-Identifier: Apache-2.0
#
# Copyright (c) 2020 Wind River Systems, Inc.
#
%global with_debug 0

%if 0%{?with_debug}
%global _dwz_low_mem_die_limit 0
%else
%global debug_package   %{nil}
%endif

Name: chartmuseum
Version: 0.12.0
Release: %{tis_patch_ver}%{?_tis_dist}
Summary: Helm Chart Repository with support for Amazon S3 and Google Cloud Storage
Group: Kubernetes
License: Apache-2.0
Source0: %{name}-%{version}.tar.gz
Source1: chartmuseum-v0.12.0-amd64
Packager: Wind River <info@windriver.com>
URL: https://github.com/helm/chartmuseum
#URL: https://s3.amazonaws.com/chartmuseum

BuildRequires: pkgconfig(systemd)
BuildRequires: pkgconfig(libseccomp)
BuildRequires: systemd-devel
BuildRequires: golang >= 1.10.0
BuildRequires: rsync
BuildRequires: go-md2man
BuildRequires: go-bindata
BuildRequires: rpm-devel >= 4.14.0
BuildRequires: rpm-libs >= 4.14.0

Requires: /bin/bash

%define CHARTMUSEUM_DIR ${HOME}/src/github.com/helm/%{name}

%description
%{summary}

%prep
%setup -q -c -n %{name}

%build
# NOTE: chartmuseum is only used to build helm charts, and is not
# part of the ISO.
# Gather the licence and readme from the source tarball.
mkdir -v -p %{CHARTMUSEUM_DIR}
mv -v %{name}/* %{CHARTMUSEUM_DIR}/
mv -v %{CHARTMUSEUM_DIR}/{LICENSE,README.md} %{name}/
pushd %{CHARTMUSEUM_DIR}
# Stub out the make to build golang package; we are using a binary.
#make
popd

%install
install -d %{buildroot}%{_bindir}
install -m 755 %{SOURCE1} %{buildroot}%{_bindir}/chartmuseum

%files
%defattr(-,root,root,-)
%doc %{name}/README.md
%license %{name}/LICENSE
%{_bindir}/chartmuseum

%changelog
