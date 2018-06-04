Name: helm
Version: 2.9.1
Release: 0%{?_tis_dist}.%{tis_patch_ver}
Summary: The Kubernetes Package Manager 
License: Apache-2.0
Group: devel
Packager: Wind River <info@windriver.com>
URL: https://github.com/kubernetes/helm/releases
Source0: %{name}-v%{version}-linux-amd64.tar.gz
Source1: tiller-2.9.1-docker-image.tgz

Requires: /bin/bash

%description
%{summary}

%prep
%setup -n linux-amd64

%install
install -d %{buildroot}%{_sbindir}
install -m 755 ${RPM_BUILD_DIR}/linux-amd64/helm %{buildroot}%{_sbindir}/helm
install -d %{buildroot}%{_sharedstatedir}/tiller
install -m 400 %{SOURCE1} %{buildroot}%{_sharedstatedir}/tiller/tiller-2.9.1-docker-image.tgz

%files
%defattr(-,root,root,-)
%{_sbindir}/helm
%{_sharedstatedir}/tiller/tiller-2.9.1-docker-image.tgz

