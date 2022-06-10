Name: helm
Version: 3.2.1
Release: 0%{?_tis_dist}.%{tis_patch_ver}
Summary: The Kubernetes Package Manager
License: Apache-2.0
Group: devel
Packager: Wind River <info@windriver.com>
URL: https://github.com/kubernetes/helm/releases
Source0: %{name}-v%{version}-linux-amd64.tar.gz
Source1: helm-upload
Source2: helm.sudo
Source3: helmv2-cli.sh
Source4: helm-2to3-0.10.0.tar.gz

Requires: /bin/bash

%description
%{summary}

%prep
%setup -n linux-amd64

# Extract helm plugins
mkdir -p ./2to3
tar zxvf %{SOURCE4} -C ./2to3

# The plugin needs to be slightly adjusted
mkdir -p ./2to3/bin
mv ./2to3/2to3 ./2to3/bin

%install
install -d %{buildroot}%{_sbindir}
install -m 755 ${RPM_BUILD_DIR}/linux-amd64/helm %{buildroot}%{_sbindir}/helm
install -d %{buildroot}/usr/local/sbin
install -m 755 %{SOURCE1} %{buildroot}/usr/local/sbin/helm-upload
install -m 755 %{SOURCE3} %{buildroot}/usr/local/sbin/helmv2-cli
install -d %{buildroot}%{_sysconfdir}/sudoers.d
install -m 440 %{SOURCE2} %{buildroot}%{_sysconfdir}/sudoers.d/helm

# Install helm plugins
install -d %{buildroot}/usr/local/share/helm
install -d %{buildroot}/usr/local/share/helm/plugins

# Install helm plugin 2to3
cp -R 2to3 %{buildroot}/usr/local/share/helm/plugins/

%files
%defattr(-,root,root,-)
%{_sbindir}/helm
/usr/local/sbin/helm-upload
/usr/local/sbin/helmv2-cli
%{_sysconfdir}/sudoers.d/helm
/usr/local/share/helm/plugins/2to3/*
