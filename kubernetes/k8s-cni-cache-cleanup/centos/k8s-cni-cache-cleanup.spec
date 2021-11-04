Name: k8s-cni-cache-cleanup
Version: 1.0
Release: 0%{?_tis_dist}.%{tis_patch_ver}
Summary: Kubernetes CNI Cache Cleanup Utility
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown
Source0: k8s-cni-cache-cleanup

Requires: /bin/bash

%description
%{summary}

%define local_dir /usr/local
%define local_sbindir %{local_dir}/sbin

%prep

%install
install -d %{buildroot}%{local_sbindir}
install -m 755 %{SOURCE0} %{buildroot}%{local_sbindir}/k8s-cni-cache-cleanup

%files
%defattr(-,root,root,-)
%{local_sbindir}/k8s-cni-cache-cleanup
