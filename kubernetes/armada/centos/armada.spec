%global git_sha     7ef4b8643b5ec5216a8f6726841e156c0aa54a1a

# Build variables
%global helm_folder /usr/lib/helm
%global toolkit_version 0.1.0
%global charts_staging ./charts

Name:           armada
Version:        0.2.0
Release:        0%{?_tis_dist}.%{tis_patch_ver}
Summary:        An orchestrator for managing a collection of Kubernetes Helm charts
License:        Apache-2.0
Group:          base
Packager:       Wind River <info@windriver.com>
URL:            https://airship-armada.readthedocs.io/
Source0:        %{name}-%{git_sha}.tar.gz

Patch1:         0001-Add-Helm-v2-client-initialization-using-tiller-postS.patch
Patch2:         0002-Tiller-wait-for-postgres-database-ping.patch
Patch3:         0003-Update-the-liveness-probe-to-verify-postgres-connect.patch
Patch4:         0004-Update-postgres-liveness-check-to-support-IPv6-addre.patch

BuildArch:      noarch

BuildRequires: helm
BuildRequires: armada-helm-toolkit
BuildRequires: chartmuseum

%description
%{summary}

%prep
%setup -n armada
%patch1 -p1
%patch2 -p1
%patch3 -p1
%patch4 -p1

%build
# Package the armada chart tarball using methodology derived from:
#   git clone https://opendev.org/airship/armada.git && cd armada
#   make charts
#
# This provides the equivalent of 'make charts' and builds what is
# minimally sufficient to generate the armada chart tarball.
# - do not need to build helm-toolkit.
# - do not need to build tiller (armada chart contains tiller).
# - This does not download helm v2 or helm-toolkit as done by 'make charts',
#   and does not require external network.
# - Everything else provided by the armada Makefile build is ignored.
#
# This is built using helm v3.
# - 'helm init' and 'helm serv' have been removed in helm v3
# - chartmuseum is drop-in replacement for 'helm serv'
# - no initial repository exist
# - charts self-contain helm-toolkit and pass lint; requirements.yaml
#   dependencies are safely removed from package so the cluster does
#   not have to serve 'local' repo (i.e., with ChartMuseum).
# - helm config of setup directories and repositories is automated
#   (we don't need to create them)

# Stage helm-toolkit in the local repo
cp %{helm_folder}/armada-helm-toolkit-%{toolkit_version}.tgz %{charts_staging}/helm-toolkit-%{toolkit_version}.tgz

# Host a local server for the charts.
chartmuseum --debug --port=8879 --context-path='/charts' --storage="local" --storage-local-rootdir="%{charts_staging}" &
sleep 2
helm repo add local http://localhost:8879/charts

cd %{charts_staging}
helm dependency update armada
helm lint armada
rm -v -f ./requirements.lock ./requirements.yaml
helm template --set pod.resources.enabled=true armada
helm package armada
cd -

# Terminate helm server (the last backgrounded task)
kill %1

%install
install -d -m 755 ${RPM_BUILD_ROOT}/opt/extracharts
install -p -D -m 755 %{charts_staging}/armada-*.tgz ${RPM_BUILD_ROOT}/opt/extracharts

%files
%defattr(-,root,root,-)
/opt/extracharts/*

