# Build variables
%global app_folder /usr/local/share/applications/helm

Summary: StarlingX nvidia gpu-operator helm chart
Name: gpu-operator
Version: 1.6.0
Release: 0%{?_tis_dist}.%{tis_patch_ver}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: https://github.com/NVIDIA/gpu-operator/tree/gh-pages

Source0: %{name}-%{version}.tar.gz

BuildArch: noarch

Patch01: deployments-setup-configmap-with-assets-for-volumemo.patch
Patch02: enablement-support-on-starlingx-cloud-platform.patch

BuildRequires: helm

%define debug_package %{nil}
%description
StarlingX port of NVIDIA gpu-operator

%prep
%setup

%patch01 -p1
%patch02 -p1

%build
cp -r assets deployments/gpu-operator/assets

helm lint deployments/gpu-operator
mkdir build_results
helm package --version %{version} --app-version %{version} -d build_results deployments/gpu-operator

%install
install -d -m 755 ${RPM_BUILD_ROOT}%{helm_folder}
install -p -D -m 755 build_results/%{name}-%{version}.tgz ${RPM_BUILD_ROOT}%{helm_folder}

%files
%defattr(-,root,root,-)
%{helm_folder}
