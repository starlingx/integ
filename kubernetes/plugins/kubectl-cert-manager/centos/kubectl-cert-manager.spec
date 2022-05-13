Summary: Cert-Manager Kubernetes plugin

Name: kubectl-cert-manager
Version: 1.7.1
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: https://github.com/cert-manager/cert-manager/releases/download/v1.7.1/kubectl-cert_manager-linux-amd64.tar.gz

Source0: kubectl-cert_manager-linux-amd64.tar.gz

%description
Cert-Manager Kubernetes plugin

%prep
cp %{SOURCE0} .
tar -xvf kubectl-cert_manager-linux-amd64.tar.gz

%install
install -d -m 755 %{buildroot}/usr/local/sbin
install -p -D -m 755 %{_builddir}/kubectl-cert_manager %{buildroot}/usr/local/sbin

%files
%defattr(-,root,root,-)
/usr/local/sbin/kubectl-cert_manager
