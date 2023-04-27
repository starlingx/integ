#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (c) 2021 Wind River Systems, Inc.
#

%define debug_package %{nil}
%define local_sbindir /usr/local/sbin

%global _k8s_name kubernetes

# Used to simplify the paths for install and files
%global _curr_stage1 %{_exec_prefix}/local/kubernetes/current/stage1
%global _curr_stage2 %{_exec_prefix}/local/kubernetes/current/stage2

# https://github.com/kubernetes/contrib
%global con_provider            github
%global con_provider_tld        com
%global con_project             kubernetes
%global con_repo                kubernetes-contrib
%global con_commit              1.18.1

##############################################
Name: kubernetes-unversioned
Version: 1.0
Release: 1%{?_tis_dist}.%{tis_patch_ver}
Summary: Kubernetes unversioned common config and current version symlinks
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown

Source0: LICENSE
Source1: %{con_repo}-v%{con_commit}.tar.gz

# systemd resource control enable CPU and Memory accounting for cgroups
Source2: kubernetes-accounting.conf

# kubelet config overrides parameters
Source3: kubelet_override.yaml

Source5: sanitize_kubelet_reserved_cpus.sh

Patch1: kubelet-service-remove-docker-dependency.patch

BuildArch: noarch

BuildRequires: systemd-devel

Requires: /bin/bash
Requires: systemd

%description
%{summary}

%prep
%setup -q -n %{con_repo}-%{con_commit} -T -b 1
mkdir contrib
cp -r ../%{con_repo}-%{con_commit}/init contrib/.
%patch1 -p1

cp %{SOURCE0} .

%build

%install
stage1_link() {
    ln -v -sf %{_curr_stage1}$1/$2 %{buildroot}$1/$2
}
stage2_link() {
    ln -v -sf %{_curr_stage2}$1/$2 %{buildroot}$1/$2
}

# Current staged directories
install -v -m 755 -d %{buildroot}%{_curr_stage1}
install -v -m 755 -d %{buildroot}%{_curr_stage2}

# Symlink targets
install -v -m 755 -d %{buildroot}%{_bindir}
install -v -m 755 -d %{buildroot}%{_sysconfdir}/systemd/system/kubelet.service.d
install -v -m 755 -d %{buildroot}%{_datadir}/bash-completion/completions
stage1_link %{_bindir} kubeadm
stage2_link %{_sysconfdir}/systemd/system/kubelet.service.d kubeadm.conf
stage2_link %{_datadir}/bash-completion/completions kubectl
stage2_link %{_bindir} kubelet-cgroup-setup.sh
stage2_link %{_bindir} kubelet
stage2_link %{_bindir} kubectl

# install environment files
install -v -d -m 0755 %{buildroot}%{_sysconfdir}/%{_k8s_name}
install -v -m 644 -t %{buildroot}%{_sysconfdir}/%{_k8s_name} contrib/init/systemd/environ/{config,kubelet,kubelet.kubeconfig,proxy}

# install config files
install -v -d -m 0755 %{buildroot}%{_tmpfilesdir}
install -v -p -m 0644 -t %{buildroot}/%{_tmpfilesdir} contrib/init/systemd/tmpfiles.d/kubernetes.conf
mkdir -p %{buildroot}/run
install -v -d -m 0755 %{buildroot}/run/%{_k8s_name}/
install -p -D -m 644 %{SOURCE3} %{buildroot}%{_sysconfdir}/%{_k8s_name}/kubelet_override.yaml

install -d %{buildroot}%{local_sbindir}
# install execution scripts
install -m 700 %{SOURCE5} %{buildroot}/%{local_sbindir}/sanitize_kubelet_reserved_cpus.sh

# install service files
install -v -d -m 0755 %{buildroot}%{_unitdir}
install -v -m 0644 -t %{buildroot}%{_unitdir} contrib/init/systemd/kubelet.service

# install the place the kubelet defaults to put volumes (/var/lib/kubelet)
install -v -d %{buildroot}%{_sharedstatedir}/kubelet

# enable CPU and Memory accounting
install -v -d -m 0755 %{buildroot}/%{_sysconfdir}/systemd/system.conf.d
install -v -p -m 0644 -t %{buildroot}/%{_sysconfdir}/systemd/system.conf.d %{SOURCE2}

%files
%defattr(-,root,root,-)
%license LICENSE
%dir %{_curr_stage1}
%dir %{_curr_stage2}

# the following are execution scripts
%{local_sbindir}/sanitize_kubelet_reserved_cpus.sh

# the following are symlinks
%{_bindir}/kubeadm
%{_bindir}/kubelet
%{_bindir}/kubelet-cgroup-setup.sh
%{_bindir}/kubectl
%dir %{_sysconfdir}/systemd/system/kubelet.service.d
%{_sysconfdir}/systemd/system/kubelet.service.d/kubeadm.conf
%{_datadir}/bash-completion/completions/kubectl

# the following are common config, environment, service
%{_unitdir}/kubelet.service
%dir %{_sharedstatedir}/kubelet
%dir %{_sysconfdir}/%{_k8s_name}
%config(noreplace) %{_sysconfdir}/%{_k8s_name}/config
%config(noreplace) %{_sysconfdir}/%{_k8s_name}/kubelet
%config(noreplace) %{_sysconfdir}/%{_k8s_name}/kubelet.kubeconfig
%config(noreplace) %{_sysconfdir}/%{_k8s_name}/kubelet_override.yaml
%config(noreplace) %{_sysconfdir}/%{_k8s_name}/proxy
%config(noreplace) %{_sysconfdir}/systemd/system.conf.d/kubernetes-accounting.conf
%{_tmpfilesdir}/kubernetes.conf
%verify(not size mtime md5) %attr(755, root,root) %dir /run/%{_k8s_name}

%changelog
