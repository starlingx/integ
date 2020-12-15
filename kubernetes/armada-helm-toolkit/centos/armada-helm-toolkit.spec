%global src_name openstack-helm-infra
%global sha c9d6676bf9a5aceb311dc31dadd07cba6a3d6392
%global helm_folder  /usr/lib/helm

Summary: Openstack-Helm-Infra helm-toolkit chart
Name: armada-helm-toolkit
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: https://github.com/openstack/openstack-helm-infra

Source0: %{src_name}-%{sha}.tar.gz

BuildArch:     noarch

# Note patches 0003, 0005, 0007 through 0013 do not apply to helm-toolkit
Patch01: 0001-Allow-multiple-containers-per-daemonset-pod.patch
Patch02: 0002-Add-imagePullSecrets-in-service-account.patch
Patch04: 0004-Partial-revert-of-31e3469d28858d7b5eb6355e88b6f49fd6.patch
Patch06: 0006-Fix-pod-restarts-on-all-workers-when-worker-added-re.patch

BuildRequires: helm
BuildRequires: chartmuseum

%description
Openstack Helm Infra helm-toolkit chart

%prep
%setup -n openstack-helm-infra
%patch01 -p1
%patch02 -p1
%patch04 -p1
%patch06 -p1


%build
# Host a server for the charts
chartmuseum --debug --port=8879 --context-path='/charts' --storage="local" --storage-local-rootdir="." &
sleep 2
helm repo add local http://localhost:8879/charts

# Make the charts. These produce tgz files
make helm-toolkit
# Both armada-helm-toolkit and openstack-helm-infra provide the same
# helm-toolkit tarball filename. Rename files with 'armada-' prefix
# to prevent 'Transaction check error'.
for filename in *.tgz; do mv -v "$filename" "armada-$filename"; done

# terminate helm server (the last backgrounded task)
kill %1

%install
install -d -m 755 ${RPM_BUILD_ROOT}%{helm_folder}
install -p -D -m 755 *.tgz ${RPM_BUILD_ROOT}%{helm_folder}

%files
%dir %attr(0755,root,root) %{helm_folder}
%defattr(-,root,root,-)
%{helm_folder}/*
