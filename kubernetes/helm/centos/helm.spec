Name: helm
Version: 2.9.1
Release: 0%{?_tis_dist}.%{tis_patch_ver}
Summary: The Kubernetes Package Manager 
License: Apache-2.0
Group: devel
Packager: Wind River <info@windriver.com>
URL: https://github.com/kubernetes/helm/releases
Source0: %{name}-v%{version}-linux-amd64.tar.gz
Source1: helm-upload
Source2: helm.sudo

Requires: /bin/bash

%description
%{summary}

%prep
%setup -n linux-amd64

%install
install -d %{buildroot}%{_sbindir}
install -m 755 ${RPM_BUILD_DIR}/linux-amd64/helm %{buildroot}%{_sbindir}/helm
install -d %{buildroot}/usr/local/sbin
install -m 755 %{SOURCE1} %{buildroot}/usr/local/sbin/helm-upload
install -d %{buildroot}%{_sysconfdir}/sudoers.d
install -m 440 %{SOURCE2} %{buildroot}%{_sysconfdir}/sudoers.d/helm

%files
%defattr(-,root,root,-)
%{_sbindir}/helm
/usr/local/sbin/helm-upload
%{_sysconfdir}/sudoers.d/helm
