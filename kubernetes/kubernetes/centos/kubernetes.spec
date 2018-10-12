%if 0%{?fedora}
%global with_devel   1
%global with_bundled 0
%global with_debug   1
%else
%global with_devel   0
%global with_bundled 1
%global with_debug   0
%endif

%if 0%{?with_debug}
# https://bugzilla.redhat.com/show_bug.cgi?id=995136#c12
%global _dwz_low_mem_die_limit 0
%else
%global debug_package %{nil}
%endif

%global provider                github
%global provider_tld            com
%global project                 kubernetes
%global repo                    kubernetes
# https://github.com/kubernetes/kubernetes

%global provider_prefix         %{provider}.%{provider_tld}/%{project}/%{repo}
%global import_path             k8s.io/kubernetes
%global commit                  1.12.1

%global con_provider            github
%global con_provider_tld        com
%global con_project             kubernetes
%global con_repo                kubernetes-contrib
# https://github.com/kubernetes/contrib
%global con_commit              1.12.1

%global kube_version            1.12.1
%global kube_git_version        v%{kube_version}

# Needed otherwise "version_ldflags=$(kube::version_ldflags)" doesn't work
%global _buildshell  /bin/bash
%global _checkshell  /bin/bash

##############################################
Name:           kubernetes
Version:        %{kube_version}
Release:        1%{?_tis_dist}.%{tis_patch_ver}
Summary:        Container cluster management
License:        ASL 2.0
URL:            https://%{import_path}
ExclusiveArch:  x86_64 aarch64 ppc64le s390x
Source0:        %{project}-v%{kube_version}.tar.gz
Source1:        %{con_repo}-v%{con_commit}.tar.gz
Source3:        kubernetes-accounting.conf
Source4:        kubeadm.conf

Source33:       genmanpages.sh

# It obsoletes cadvisor but needs its source code (literally integrated)
Obsoletes:      cadvisor

# kubernetes is decomposed into master and node subpackages
# require both of them for updates
Requires: kubernetes-master = %{version}-%{release}
Requires: kubernetes-node = %{version}-%{release}

%description
%{summary}

%if 0%{?with_devel}
%package devel
Summary:       %{summary}
BuildArch:      noarch

Provides: golang(%{import_path}/cmd/genutils) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/kube-apiserver/app) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/kube-apiserver/app/options) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/kube-controller-manager/app) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/kube-controller-manager/app/options) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/kube-proxy/app) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/kube-proxy/app/options) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/kubectl/app) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/kubelet/app) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/kubelet/app/options) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/args) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/client-gen/args) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/client-gen/generators) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/client-gen/generators/fake) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/client-gen/generators/normalization) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/client-gen/test_apis/testgroup.k8s.io) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/client-gen/test_apis/testgroup.k8s.io/install) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/client-gen/test_apis/testgroup.k8s.io/v1) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/client-gen/testoutput/clientset_generated/test_internalclientset) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/client-gen/testoutput/clientset_generated/test_internalclientset/fake) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/client-gen/testoutput/clientset_generated/test_internalclientset/typed/testgroup.k8s.io/unversioned) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/client-gen/testoutput/clientset_generated/test_internalclientset/typed/testgroup.k8s.io/unversioned/fake) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/conversion-gen/generators) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/deepcopy-gen/generators) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/generator) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/go-to-protobuf/protobuf) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/import-boss/generators) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/namer) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/parser) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/set-gen/generators) = %{version}-%{release}
Provides: golang(%{import_path}/cmd/libs/go2idl/types) = %{version}-%{release}
Provides: golang(%{import_path}/federation/apis/federation) = %{version}-%{release}
Provides: golang(%{import_path}/federation/apis/federation/install) = %{version}-%{release}
Provides: golang(%{import_path}/federation/apis/federation/v1beta1) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_internalclientset) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_internalclientset/fake) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_internalclientset/typed/core/unversioned) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_internalclientset/typed/core/unversioned/fake) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_internalclientset/typed/extensions/unversioned) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_internalclientset/typed/extensions/unversioned/fake) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_internalclientset/typed/federation/unversioned) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_internalclientset/typed/federation/unversioned/fake) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_release_1_3) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_release_1_3/fake) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_release_1_3/typed/core/v1) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_release_1_3/typed/core/v1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_release_1_3/typed/federation/v1beta1) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_release_1_3/typed/federation/v1beta1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_release_1_4) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_release_1_4/fake) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_release_1_4/typed/core/v1) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_release_1_4/typed/core/v1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_release_1_4/typed/extensions/v1beta1) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_release_1_4/typed/extensions/v1beta1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_release_1_4/typed/federation/v1beta1) = %{version}-%{release}
Provides: golang(%{import_path}/federation/client/clientset_generated/federation_release_1_4/typed/federation/v1beta1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/federation/pkg/federation-controller/util) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/admission) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/annotations) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/endpoints) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/errors) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/errors/storage) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/install) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/meta) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/meta/metatypes) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/pod) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/resource) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/rest) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/rest/resttest) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/service) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/testapi) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/testing/compat) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/unversioned) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/unversioned/validation) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/util) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/v1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/api/validation) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apimachinery) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apimachinery/registered) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/abac) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/abac/latest) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/abac/v0) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/abac/v1beta1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/apps) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/apps/install) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/apps/v1alpha1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/apps/validation) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/authentication) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/authentication/install) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/authentication/v1beta1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/authorization) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/authorization/install) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/authorization/v1beta1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/authorization/validation) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/autoscaling) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/autoscaling/install) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/autoscaling/v1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/autoscaling/validation) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/batch) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/batch/install) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/batch/v1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/batch/v2alpha1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/batch/validation) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/certificates) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/certificates/install) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/certificates/v1alpha1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/certificates/validation) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/componentconfig) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/componentconfig/install) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/componentconfig/v1alpha1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/extensions) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/extensions/install) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/extensions/v1beta1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/extensions/validation) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/imagepolicy) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/imagepolicy/install) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/imagepolicy/v1alpha1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/policy) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/policy/install) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/policy/v1alpha1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/policy/validation) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/rbac) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/rbac/install) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/rbac/v1alpha1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/rbac/validation) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/storage) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/storage/install) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/storage/v1beta1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apis/storage/validation) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apiserver) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apiserver/audit) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apiserver/authenticator) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apiserver/metrics) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/apiserver/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/auth/authenticator) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/auth/authenticator/bearertoken) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/auth/authorizer) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/auth/authorizer/abac) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/auth/authorizer/union) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/auth/handlers) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/auth/user) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/capabilities) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/cache) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/chaosclient) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/authentication/unversioned) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/authentication/unversioned/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/authorization/unversioned) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/authorization/unversioned/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/autoscaling/unversioned) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/autoscaling/unversioned/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/batch/unversioned) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/batch/unversioned/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/certificates/unversioned) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/certificates/unversioned/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/core/unversioned) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/core/unversioned/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/extensions/unversioned) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/extensions/unversioned/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/rbac/unversioned) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/rbac/unversioned/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/storage/unversioned) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/internalclientset/typed/storage/unversioned/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_2) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_2/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_2/typed/core/v1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_2/typed/core/v1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_2/typed/extensions/v1beta1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_2/typed/extensions/v1beta1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_3) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_3/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_3/typed/autoscaling/v1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_3/typed/autoscaling/v1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_3/typed/batch/v1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_3/typed/batch/v1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_3/typed/core/v1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_3/typed/core/v1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_3/typed/extensions/v1beta1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_3/typed/extensions/v1beta1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_4) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_4/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_4/typed/authorization/v1beta1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_4/typed/authorization/v1beta1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_4/typed/autoscaling/v1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_4/typed/autoscaling/v1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_4/typed/batch/v1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_4/typed/batch/v1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_4/typed/core/v1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_4/typed/core/v1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_4/typed/extensions/v1beta1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_4/typed/extensions/v1beta1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_4/typed/policy/v1alpha1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/clientset_generated/release_1_4/typed/policy/v1alpha1/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/leaderelection) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/metrics) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/metrics/prometheus) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/record) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/restclient) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/testing/core) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/transport) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/typed/discovery) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/typed/discovery/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/typed/dynamic) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/unversioned) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/unversioned/adapters/internalclientset) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/unversioned/auth) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/unversioned/clientcmd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/unversioned/clientcmd/api) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/unversioned/clientcmd/api/latest) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/unversioned/clientcmd/api/v1) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/unversioned/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/unversioned/portforward) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/unversioned/remotecommand) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/unversioned/testclient) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/client/unversioned/testclient/simple) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/cloudprovider) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/cloudprovider/providers) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/cloudprovider/providers/aws) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/cloudprovider/providers/azure) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/cloudprovider/providers/cloudstack) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/cloudprovider/providers/fake) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/cloudprovider/providers/gce) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/cloudprovider/providers/mesos) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/cloudprovider/providers/openstack) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/cloudprovider/providers/ovirt) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/cloudprovider/providers/rackspace) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/cloudprovider/providers/vsphere) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/certificates) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/daemon) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/deployment) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/deployment/util) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/disruption) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/endpoint) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/framework) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/framework/informers) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/garbagecollector) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/garbagecollector/metaonly) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/job) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/namespace) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/node) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/petset) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/podautoscaler) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/podautoscaler/metrics) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/podgc) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/replicaset) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/replicaset/options) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/replication) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/resourcequota) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/route) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/scheduledjob) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/service) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/serviceaccount) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/volume/attachdetach) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/volume/attachdetach/cache) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/volume/attachdetach/populator) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/volume/attachdetach/reconciler) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/volume/attachdetach/statusupdater) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/volume/attachdetach/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/volume/persistentvolume) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/controller/volume/persistentvolume/options) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/conversion) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/conversion/queryparams) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/credentialprovider) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/credentialprovider/aws) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/credentialprovider/gcp) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/dns) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/fieldpath) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/fields) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/genericapiserver) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/genericapiserver/authorizer) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/genericapiserver/openapi) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/genericapiserver/options) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/genericapiserver/validation) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/healthz) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/httplog) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/hyperkube) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubectl) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubectl/cmd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubectl/cmd/config) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubectl/cmd/rollout) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubectl/cmd/set) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubectl/cmd/templates) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubectl/cmd/util) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubectl/cmd/util/editor) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubectl/cmd/util/jsonmerge) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubectl/metricsutil) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubectl/resource) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubectl/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/api) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/api/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/api/v1alpha1/runtime) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/api/v1alpha1/stats) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/cadvisor) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/cadvisor/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/client) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/cm) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/config) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/container) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/container/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/custommetrics) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/dockershim) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/dockertools) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/envvars) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/events) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/eviction) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/images) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/kuberuntime) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/leaky) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/lifecycle) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/metrics) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/network) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/network/cni) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/network/cni/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/network/exec) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/network/hairpin) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/network/hostport) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/network/hostport/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/network/kubenet) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/network/mock_network) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/network/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/pleg) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/pod) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/pod/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/prober) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/prober/results) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/prober/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/qos) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/remote) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/rkt) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/rkt/mock_os) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/rktshim) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/server) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/server/portforward) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/server/remotecommand) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/server/stats) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/status) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/sysctl) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/types) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/util) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/util/cache) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/util/format) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/util/ioutils) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/util/queue) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/util/sliceutils) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/volumemanager) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/volumemanager/cache) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/volumemanager/populator) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubelet/volumemanager/reconciler) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/kubemark) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/labels) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/master) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/master/ports) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/metrics) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/probe) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/probe/exec) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/probe/http) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/probe/tcp) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/proxy) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/proxy/config) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/proxy/healthcheck) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/proxy/iptables) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/proxy/userspace) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/quota) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/quota/evaluator/core) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/quota/generic) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/quota/install) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/authorization/subjectaccessreview) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/authorization/util) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/cachesize) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/certificates) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/certificates/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/clusterrole) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/clusterrole/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/clusterrole/policybased) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/clusterrolebinding) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/clusterrolebinding/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/clusterrolebinding/policybased) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/componentstatus) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/configmap) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/configmap/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/controller) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/controller/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/daemonset) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/daemonset/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/deployment) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/deployment/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/endpoint) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/endpoint/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/event) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/event/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/experimental/controller/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/generic) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/generic/registry) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/generic/rest) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/horizontalpodautoscaler) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/horizontalpodautoscaler/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/ingress) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/ingress/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/job) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/job/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/limitrange) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/limitrange/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/namespace) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/namespace/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/networkpolicy) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/networkpolicy/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/node) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/node/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/node/rest) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/persistentvolume) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/persistentvolume/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/persistentvolumeclaim) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/persistentvolumeclaim/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/petset) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/petset/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/pod) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/pod/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/pod/rest) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/poddisruptionbudget) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/poddisruptionbudget/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/podsecuritypolicy) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/podsecuritypolicy/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/podtemplate) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/podtemplate/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/rangeallocation) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/registrytest) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/replicaset) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/replicaset/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/resourcequota) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/resourcequota/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/role) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/role/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/role/policybased) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/rolebinding) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/rolebinding/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/rolebinding/policybased) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/scheduledjob) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/scheduledjob/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/secret) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/secret/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/securitycontextconstraints) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/securitycontextconstraints/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/service) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/service/allocator) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/service/allocator/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/service/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/service/ipallocator) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/service/ipallocator/controller) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/service/ipallocator/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/service/portallocator) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/service/portallocator/controller) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/serviceaccount) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/serviceaccount/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/storageclass) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/storageclass/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/thirdpartyresource) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/thirdpartyresource/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/thirdpartyresourcedata) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/thirdpartyresourcedata/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/registry/tokenreview) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/runtime) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/runtime/serializer) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/runtime/serializer/json) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/runtime/serializer/protobuf) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/runtime/serializer/recognizer) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/runtime/serializer/streaming) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/runtime/serializer/versioning) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/runtime/serializer/yaml) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/security) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/security/apparmor) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/security/podsecuritypolicy) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/security/podsecuritypolicy/apparmor) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/security/podsecuritypolicy/capabilities) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/security/podsecuritypolicy/group) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/security/podsecuritypolicy/selinux) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/security/podsecuritypolicy/sysctl) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/security/podsecuritypolicy/user) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/security/podsecuritypolicy/util) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/securitycontext) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/securitycontextconstraints) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/securitycontextconstraints/capabilities) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/securitycontextconstraints/group) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/securitycontextconstraints/seccomp) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/securitycontextconstraints/selinux) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/securitycontextconstraints/user) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/securitycontextconstraints/util) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/selection) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/serviceaccount) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/ssh) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/storage) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/storage/etcd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/storage/etcd/etcdtest) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/storage/etcd/metrics) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/storage/etcd/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/storage/etcd/testing/testingcert) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/storage/etcd/util) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/storage/etcd3) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/storage/storagebackend) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/storage/storagebackend/factory) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/storage/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/types) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/ui) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/async) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/bandwidth) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/cache) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/certificates) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/chmod) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/chown) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/clock) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/codeinspector) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/config) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/configz) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/crlf) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/crypto) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/dbus) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/diff) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/ebtables) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/env) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/errors) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/exec) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/flag) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/flock) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/flowcontrol) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/flushwriter) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/framer) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/goroutinemap) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/goroutinemap/exponentialbackoff) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/hash) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/homedir) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/httpstream) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/httpstream/spdy) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/integer) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/interrupt) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/intstr) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/io) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/iptables) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/iptables/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/json) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/jsonpath) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/keymutex) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/labels) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/limitwriter) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/logs) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/maps) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/metrics) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/mount) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/net) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/net/sets) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/node) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/oom) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/parsers) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/pod) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/procfs) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/proxy) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/rand) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/replicaset) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/resourcecontainer) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/rlimit) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/runtime) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/selinux) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/sets) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/sets/types) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/slice) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/strategicpatch) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/strings) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/sysctl) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/sysctl/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/system) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/term) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/threading) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/uuid) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/validation) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/validation/field) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/wait) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/workqueue) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/wsstream) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/util/yaml) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/version) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/version/prometheus) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/version/verflag) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/aws_ebs) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/azure_dd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/azure_file) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/cephfs) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/cinder) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/configmap) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/downwardapi) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/empty_dir) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/fc) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/flexvolume) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/flocker) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/gce_pd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/git_repo) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/glusterfs) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/host_path) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/iscsi) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/nfs) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/quobyte) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/rbd) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/secret) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/testing) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/util) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/util/nestedpendingoperations) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/util/operationexecutor) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/util/types) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/util/volumehelper) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/volume/vsphere_volume) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/watch) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/watch/json) = %{version}-%{release}
Provides: golang(%{import_path}/pkg/watch/versioned) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/cmd/kube-scheduler/app) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/cmd/kube-scheduler/app/options) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/admit) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/alwayspullimages) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/antiaffinity) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/deny) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/exec) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/imagepolicy) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/initialresources) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/limitranger) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/namespace/autoprovision) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/namespace/exists) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/namespace/lifecycle) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/persistentvolume/label) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/resourcequota) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/security) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/security/podsecuritypolicy) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/securitycontext/scdeny) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/serviceaccount) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/admission/storageclass/default) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth/authenticator) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth/authenticator/password) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth/authenticator/password/allow) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth/authenticator/password/keystone) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth/authenticator/password/passwordfile) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth/authenticator/request/basicauth) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth/authenticator/request/union) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth/authenticator/request/x509) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth/authenticator/token/oidc) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth/authenticator/token/oidc/testing) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth/authenticator/token/tokenfile) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth/authenticator/token/tokentest) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth/authenticator/token/webhook) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth/authorizer) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth/authorizer/rbac) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/auth/authorizer/webhook) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/client/auth) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/client/auth/gcp) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/client/auth/oidc) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/scheduler) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/scheduler/algorithm) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/scheduler/algorithm/predicates) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/scheduler/algorithm/priorities) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/scheduler/algorithm/priorities/util) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/scheduler/algorithmprovider) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/scheduler/algorithmprovider/defaults) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/scheduler/api) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/scheduler/api/latest) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/scheduler/api/v1) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/scheduler/api/validation) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/scheduler/factory) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/scheduler/metrics) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/scheduler/schedulercache) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/scheduler/testing) = %{version}-%{release}
Provides: golang(%{import_path}/plugin/pkg/webhook) = %{version}-%{release}

%description devel
Libraries for building packages importing k8s.io/kubernetes.
Currently, the devel is not suitable for development.
It is meant only as a buildtime dependency for other projects.

This package contains library source intended for
building other packages which use %{project}/%{repo}.
%endif

##############################################
%package unit-test
Summary: %{summary} - for running unit tests

# below Rs used for testing
Requires: golang >= 1.2-7
Requires: etcd >= 2.0.9
Requires: hostname
Requires: rsync
Requires: NetworkManager

%description unit-test
%{summary} - for running unit tests

##############################################
%package master
Summary: Kubernetes services for master host

BuildRequires: golang >= 1.2-7
BuildRequires: systemd
BuildRequires: rsync
BuildRequires: go-md2man
BuildRequires: go-bindata

Requires(pre): shadow-utils
Requires: kubernetes-client = %{version}-%{release}

# if node is installed with node, version and release must be the same
Conflicts: kubernetes-node < %{version}-%{release}
Conflicts: kubernetes-node > %{version}-%{release}

%description master
Kubernetes services for master host

##############################################
%package node
Summary: Kubernetes services for node host

%if 0%{?fedora} >= 27
Requires: (docker or docker-ce)
Suggests: docker-ce
%else
Requires: docker-ce
%endif
Requires: conntrack-tools

BuildRequires: golang >=  1.10.2
BuildRequires: systemd
BuildRequires: rsync
BuildRequires: go-md2man
BuildRequires: go-bindata

Requires(pre): shadow-utils
Requires:      socat
Requires:      kubernetes-client = %{version}-%{release}

# if master is installed with node, version and release must be the same
Conflicts: kubernetes-master < %{version}-%{release}
Conflicts: kubernetes-master > %{version}-%{release}

%description node
Kubernetes services for node host

##############################################
%package  kubeadm
Summary:  Kubernetes tool for standing up clusters
Requires: kubernetes-node = %{version}-%{release}
Requires: containernetworking-cni

%description kubeadm
Kubernetes tool for standing up clusters

##############################################
%package client
Summary: Kubernetes client tools

BuildRequires: golang >= 1.2-7
BuildRequires: go-bindata

%description client
Kubernetes client tools like kubectl

##############################################

%prep
%setup -q -n %{con_repo}-%{con_commit} -T -b 1
%setup -q -n %{repo}-%{commit}

# copy contrib folder
mkdir contrib
cp -r ../%{con_repo}-%{con_commit}/init contrib/.

#src/k8s.io/kubernetes/pkg/util/certificates
# Patch the code to remove eliptic.P224 support
for dir in vendor/github.com/google/certificate-transparency/go/x509 pkg/util/certificates; do
  if [ -d "${dir}" ]; then
    pushd ${dir}
    sed -i "/^[^=]*$/ s/oidNamedCurveP224/oidNamedCurveP256/g" *.go
    sed -i "/^[^=]*$/ s/elliptic\.P224/elliptic.P256/g" *.go
    popd
  fi
done

# Move all the code under src/k8s.io/kubernetes directory
mkdir -p src/k8s.io/kubernetes
mv $(ls | grep -v "^src$") src/k8s.io/kubernetes/.

###############

%build
export PBR_VERSION=%{version}
pushd src/k8s.io/kubernetes/
export KUBE_GIT_TREE_STATE="clean"
export KUBE_GIT_COMMIT=%{commit}
export KUBE_GIT_VERSION=%{kube_git_version}
export KUBE_EXTRA_GOPATH=$(pwd)/Godeps/_workspace

# https://bugzilla.redhat.com/show_bug.cgi?id=1392922#c1
%ifarch ppc64le
export GOLDFLAGS='-linkmode=external'
%endif
make WHAT="cmd/hyperkube cmd/kube-apiserver cmd/kubeadm"

# convert md to man
./hack/generate-docs.sh || true
pushd docs
pushd admin
cp kube-apiserver.md kube-controller-manager.md kube-proxy.md kube-scheduler.md kubelet.md ..
popd
cp %{SOURCE33} genmanpages.sh
bash genmanpages.sh
popd
popd

%install
export PBR_VERSION=%{version}
pushd src/k8s.io/kubernetes/
. hack/lib/init.sh
kube::golang::setup_env

%ifarch ppc64le
output_path="_output/local/go/bin"
%else
output_path="${KUBE_OUTPUT_BINPATH}/$(kube::golang::host_platform)"
%endif

install -m 755 -d %{buildroot}%{_bindir}

echo "+++ INSTALLING hyperkube"
install -p -m 755 -t %{buildroot}%{_bindir} ${output_path}/hyperkube

echo "+++ INSTALLING kube-apiserver"
install -p -m 754 -t %{buildroot}%{_bindir} ${output_path}/kube-apiserver

echo "+++ INSTALLING kubeadm"
install -p -m 755 -t %{buildroot}%{_bindir} ${output_path}/kubeadm
install -d -m 0755 %{buildroot}/%{_sysconfdir}/systemd/system/kubelet.service.d
install -p -m 0644 -t %{buildroot}/%{_sysconfdir}/systemd/system/kubelet.service.d %{SOURCE4}

binaries=(kube-controller-manager kube-scheduler kube-proxy kubelet kubectl)
for bin in "${binaries[@]}"; do
  echo "+++ HARDLINKING ${bin} to hyperkube"
  ln %{buildroot}%{_bindir}/hyperkube %{buildroot}%{_bindir}/${bin}
done

# install the bash completion
install -d -m 0755 %{buildroot}%{_datadir}/bash-completion/completions/
%{buildroot}%{_bindir}/kubectl completion bash > %{buildroot}%{_datadir}/bash-completion/completions/kubectl

# install config files
install -d -m 0755 %{buildroot}%{_sysconfdir}/%{name}
install -m 644 -t %{buildroot}%{_sysconfdir}/%{name} contrib/init/systemd/environ/*

# install service files
install -d -m 0755 %{buildroot}%{_unitdir}
install -m 0644 -t %{buildroot}%{_unitdir} contrib/init/systemd/*.service

# install manpages
install -d %{buildroot}%{_mandir}/man1
install -p -m 644 docs/man/man1/* %{buildroot}%{_mandir}/man1
rm %{buildroot}%{_mandir}/man1/cloud-controller-manager.*
# from k8s tarball copied docs/man/man1/*.1

# install the place the kubelet defaults to put volumes
install -d %{buildroot}%{_sharedstatedir}/kubelet

# place contrib/init/systemd/tmpfiles.d/kubernetes.conf to /usr/lib/tmpfiles.d/kubernetes.conf
install -d -m 0755 %{buildroot}%{_tmpfilesdir}
install -p -m 0644 -t %{buildroot}/%{_tmpfilesdir} contrib/init/systemd/tmpfiles.d/kubernetes.conf
mkdir -p %{buildroot}/run
install -d -m 0755 %{buildroot}/run/%{name}/

# enable CPU and Memory accounting
install -d -m 0755 %{buildroot}/%{_sysconfdir}/systemd/system.conf.d
install -p -m 0644 -t %{buildroot}/%{_sysconfdir}/systemd/system.conf.d %{SOURCE3}

# source codes for building projects
%if 0%{?with_devel}
install -d -p %{buildroot}/%{gopath}/src/%{import_path}/
echo "%%dir %%{gopath}/src/%%{import_path}/." >> devel.file-list
# find all *.go but no *_test.go files and generate devel.file-list
for file in $(find . -iname "*.go" \! -iname "*_test.go") ; do
    echo "%%dir %%{gopath}/src/%%{import_path}/$(dirname $file)" >> devel.file-list
    install -d -p %{buildroot}/%{gopath}/src/%{import_path}/$(dirname $file)
    cp -pav $file %{buildroot}/%{gopath}/src/%{import_path}/$file
    echo "%%{gopath}/src/%%{import_path}/$file" >> devel.file-list
done
%endif

%if 0%{?with_devel}
sort -u -o devel.file-list devel.file-list
%endif

popd

%if 0%{?with_devel}
mv src/k8s.io/kubernetes/devel.file-list .
%endif

mv src/k8s.io/kubernetes/*.md .
mv src/k8s.io/kubernetes/LICENSE .


# place files for unit-test rpm
install -d -m 0755 %{buildroot}%{_sharedstatedir}/kubernetes-unit-test/
# basically, everything from the root directory is needed
# unit-tests needs source code
# integration tests needs docs and other files
# test-cmd.sh atm needs cluster, examples and other
cp -a src %{buildroot}%{_sharedstatedir}/kubernetes-unit-test/
rm -rf %{buildroot}%{_sharedstatedir}/kubernetes-unit-test/src/k8s.io/kubernetes/_output
cp -a *.md %{buildroot}%{_sharedstatedir}/kubernetes-unit-test/src/k8s.io/kubernetes/

%check
# Fedora, RHEL7 and CentOS are tested via unit-test subpackage
if [ 1 != 1 ]; then
echo "******Testing the commands*****"
hack/test-cmd.sh
echo "******Benchmarking kube********"
hack/benchmark-go.sh

# In Fedora 20 and RHEL7 the go cover tools isn't available correctly
%if 0%{?fedora} >= 21
echo "******Testing the go code******"
hack/test-go.sh
echo "******Testing integration******"
hack/test-integration.sh --use_go_build
%endif
fi

##############################################
%files
# empty as it depends on master and node

##############################################
%files master
%license LICENSE
%doc *.md
%{_mandir}/man1/kube-apiserver.1*
%{_mandir}/man1/kube-controller-manager.1*
%{_mandir}/man1/kube-scheduler.1*
%attr(754, -, kube) %caps(cap_net_bind_service=ep) %{_bindir}/kube-apiserver
%{_bindir}/kube-controller-manager
%{_bindir}/kube-scheduler
%{_bindir}/hyperkube
%{_unitdir}/kube-apiserver.service
%{_unitdir}/kube-controller-manager.service
%{_unitdir}/kube-scheduler.service
%dir %{_sysconfdir}/%{name}
%config(noreplace) %{_sysconfdir}/%{name}/apiserver
%config(noreplace) %{_sysconfdir}/%{name}/scheduler
%config(noreplace) %{_sysconfdir}/%{name}/config
%config(noreplace) %{_sysconfdir}/%{name}/controller-manager
%{_tmpfilesdir}/kubernetes.conf
%verify(not size mtime md5) %attr(755, kube,kube) %dir /run/%{name}

##############################################
%files node
%license LICENSE
%doc *.md
%{_mandir}/man1/kubelet.1*
%{_mandir}/man1/kube-proxy.1*
%{_bindir}/kubelet
%{_bindir}/kube-proxy
%{_bindir}/hyperkube
%{_unitdir}/kube-proxy.service
%{_unitdir}/kubelet.service
%dir %{_sharedstatedir}/kubelet
%dir %{_sysconfdir}/%{name}
%config(noreplace) %{_sysconfdir}/%{name}/config
%config(noreplace) %{_sysconfdir}/%{name}/kubelet
%config(noreplace) %{_sysconfdir}/%{name}/kubelet.kubeconfig
%config(noreplace) %{_sysconfdir}/%{name}/proxy
%config(noreplace) %{_sysconfdir}/systemd/system.conf.d/kubernetes-accounting.conf
%{_tmpfilesdir}/kubernetes.conf
%verify(not size mtime md5) %attr(755, kube,kube) %dir /run/%{name}

##############################################
%files kubeadm
%license LICENSE
%doc *.md
%{_mandir}/man1/kubeadm.1*
%{_mandir}/man1/kubeadm-*
%{_bindir}/kubeadm
%dir %{_sysconfdir}/systemd/system/kubelet.service.d
%config(noreplace) %{_sysconfdir}/systemd/system/kubelet.service.d/kubeadm.conf

##############################################
%files client
%license LICENSE
%doc *.md
%{_mandir}/man1/kubectl.1*
%{_mandir}/man1/kubectl-*
%{_bindir}/kubectl
%{_bindir}/hyperkube
%{_datadir}/bash-completion/completions/kubectl

##############################################
%files unit-test
%{_sharedstatedir}/kubernetes-unit-test/

%if 0%{?with_devel}
%files devel -f devel.file-list
%doc *.md
%dir %{gopath}/src/k8s.io
%endif

##############################################

%pre master
getent group kube >/dev/null || groupadd -r kube
getent passwd kube >/dev/null || useradd -r -g kube -d / -s /sbin/nologin \
        -c "Kubernetes user" kube

%post master
%systemd_post kube-apiserver kube-scheduler kube-controller-manager

%preun master
%systemd_preun kube-apiserver kube-scheduler kube-controller-manager

%postun master
%systemd_postun


%pre node
getent group kube >/dev/null || groupadd -r kube
getent passwd kube >/dev/null || useradd -r -g kube -d / -s /sbin/nologin \
        -c "Kubernetes user" kube

%post node
%systemd_post kubelet kube-proxy
# If accounting is not currently enabled systemd reexec
if [[ `systemctl show docker kubelet | grep -q -e CPUAccounting=no -e MemoryAccounting=no; echo $?` -eq 0 ]]; then
  systemctl daemon-reexec
fi

%preun node
%systemd_preun kubelet kube-proxy

%postun node
%systemd_postun

############################################
%changelog
* Tue Mar 27 2018 Spyros Trigazis <strigazi@gmail.com> - 1.10.0-1
- Bump to upstream v1.10.0

* Thu Mar 22 2018 Spyros Trigazis <strigazi@gmail.com> - 1.9.6-1
- Bump to upstream v1.9.6

* Tue Mar 20 2018 Jan Chaloupka <jchaloup@redhat.com> - 1.9.5-1
- Bump to upstream v1.9.5
  resolves: #1554420

* Sun Feb 11 2018 Spyros Trigazis <strigazi@gmail.com> - 1.9.3-1
- Bump to upstream v1.9.3

* Fri Feb 09 2018 Jan Chaloupka <jchaloup@redhat.com> - 1.9.1-5
- Add --fail-swap-on=false flag to the /etc/kubernetes/kubelet
  resolves: #1542476

* Thu Feb 08 2018 Igor Gnatenko <ignatenkobrain@fedoraproject.org> - 1.9.1-4
- Escape macro in %%changelog

* Wed Feb 07 2018 Fedora Release Engineering <releng@fedoraproject.org> - 1.9.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Mon Jan 15 2018 Jan Chaloupka <jchaloup@redhat.com> - 1.9.1-2
- If docker is not available, try docker-ce instead (use boolean dependencies)
  resolves: #1534508

* Fri Jan 12 2018 Spyros Trigazis <strigazi@gmail.com> - 1.9.1-1
- Update to upstream v1.9.1
  resolves #1533794

* Tue Oct 24 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.8.1-1
- Update to upstream v1.8.1
  resolves: #1497135

* Mon Oct 02 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.8.0-1
- Update to upstream v1.8.0
  related: #1497625

* Mon Oct 02 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.7.7-1
- Update to upstream v1.7.7
  resolves: #1497625

* Mon Sep 18 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.7.6-1
- Update to upstream v1.7.6
  resolves: #1492551

* Mon Sep 11 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.7.5-1
- Update to upstream v1.7.5
  resolves: #1490316

* Fri Aug 18 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.7.4-1
- Fix the version
  related: #1482874

* Fri Aug 18 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.7.3-2
- Update to upstream v1.7.4
  resolves: #1482874

* Tue Aug 08 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.7.3-1
- Update to upstream v1.7.3
  resolves: #1479685

* Thu Aug 03 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.7.2-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Sun Jul 30 2017 Florian Weimer <fweimer@redhat.com> - 1.7.2-3
- Rebuild with binutils fix for ppc64le (#1475636)

* Wed Jul 26 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.7.2-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Mon Jul 24 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.7.2-1
- Update to upstream v1.7.2

* Mon Jul 24 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.7.1-2
- Sync kubeadm.conf with upstream service configuration (set Restart,StartLimitInterval,RestartSec)

* Fri Jul 14 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.7.1-1
- Update to upstream v1.7.1
  resolves: #1471767

* Sat Jul 08 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.6.7-1
- Update to upstream v1.6.7
  resolves: #1468823
  resolves: #1468752

* Fri May 19 2017 Timothy St. Clair <tstclair@heptio.com> - 1.6.4-1
- Add kubeadm subpackage to enable upstream deployments

* Thu May 18 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.6.3-1
- Update to upstream v1.6.3
  resolves: #1452101

* Fri May 12 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.6.2-2
- Extend archs with s390x
  resolves: #1400000

* Tue May 02 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.6.2-1
- Update to upstream v1.6.2
  resolves: #1447338

* Tue Apr 11 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.6.1-1
- Update to upstream v1.6.1
  related: #1422889

* Fri Mar 31 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.5.6-1
- Update to upstream v1.5.6
  related: #1422889

* Mon Mar 27 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.5.5-4
- Update to upstream v1.5.5
  related: #1422889

* Mon Mar 27 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.5.4-3
- re-enable debug-info
  related: #1422889

* Thu Mar 09 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.5.4-2
- Bump to upstream 7243c69eb523aa4377bce883e7c0dd76b84709a1
  related: #1422889

* Thu Feb 16 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.5.3-1
- Update to upstream v1.5.3
  resolves: #1422889

* Fri Feb 10 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.5.2-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Wed Jan 18 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.5.2-2
- fix rootScopeNaming generate selfLink
  resolves: #1413997

* Fri Jan 13 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.5.2-1
- Bump version as well
  related: #1412996

* Fri Jan 13 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.5.1-2
- Bump to upstream 1.5.2
  resolves: #1412996

* Thu Jan 05 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.5.1-1
- Bump to upstream 1.5.1
  resolves: #1410186

* Wed Jan 04 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.4.7-2
- Generate the md files before they are converted to man pages
  resolves: #1409943

* Mon Dec 12 2016 Jan Chaloupka <jchaloup@redhat.com> - 1.4.7-1
- Bump to upstream v1.4.7
  resolves: #1403823
  New conntrack-tools dependency of kube-proxy
  Build kubernetes on ppc64le with linkmode=external
  resolves: #1392922

* Mon Nov 14 2016 jchaloup <jchaloup@redhat.com> - 1.4.5-3
- Patch unit-test subpackage to run tests over k8s distro binaries

* Wed Nov 09 2016 jchaloup <jchaloup@redhat.com> - 1.4.5-2
- Add missing if devel around generated devel.file-list
  related: #1390074

* Tue Nov 08 2016 jchaloup <jchaloup@redhat.com> - 1.4.5-1
- Bump to upstream v1.4.5 (flip back to upstream based Kubernetes)
  related: #1390074

* Mon Oct 31 2016 jchaloup <jchaloup@redhat.com> - 1.4.0-0.1.beta3.git52492b4
- Update to origin v1.4.0-alpha.0 (ppc64le and arm unbuildable with the current golang version)
  resolves: #1390074

* Mon Oct 24 2016 jchaloup <jchaloup@redhat.com> - 1.3.0-0.4.git52492b4
- Update to origin v1.3.1
  resolves: #1388092

* Thu Sep 08 2016 jchaloup <jchaloup@redhat.com> - 1.3.0-0.3.rc1.git507d3a7
- Update to origin v1.3.0-rc1
  resolves: #1374361

* Thu Aug 11 2016 Dennis Gilmore <dennis@ausil.us> -1.3.0-0.2.git4a3f9c5
- enable armv7hl and aarch64

* Tue Aug 09 2016 jchaloup <jchaloup@redhat.com> - 1.3.0-0.1.git4a3f9c5
- Update to origin v1.3.0-alpha.3
  resolves: #1365601

* Thu Jul 21 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.2.0-0.27.git4a3f9c5
- https://fedoraproject.org/wiki/Changes/golang1.7

* Sun Jul 17 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.26.git4a3f9c5
- Update to origin v1.2.1
  resolves: #1357261

* Wed Jul 13 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.25.git4a3f9c5
- Enable CPU and Memory accounting on a node

* Wed Jun 29 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.24.git4a3f9c5
- Be more verbose about devel subpackage
  resolves: #1269449

* Tue Jun 28 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.23.git4a3f9c5
- Own /run/kubernetes directory
  resolves: #1264699

* Sat May 28 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.22.git4a3f9c5
- Bump to origin v1.2.0
  resolves: #1340643

* Wed May 04 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.21.git4a3f9c5
- Extend uni-test subpackage to run other tests

* Mon Apr 25 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.20.git4a3f9c5
- Update support for ppc64le to use go compiler
  related: #1306214

* Thu Apr 21 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.19.git4a3f9c5
- Fix support for ppc64le
  related: #1306214

* Tue Apr 19 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.18.git4a3f9c5
- Bump to origin v1.1.6
  resolves: #1328357

* Mon Apr 11 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.17.alpha6.git4a3f9c5
- Don't disable extensions/v1beta1 by default to conform with upstream documentation

* Wed Mar 30 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.16.alpha6.git4a3f9c5
  Update to origin's v1.1.5
  Build on ppc64le as well
  resolves: #1306214

* Tue Mar 08 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.15.alpha6.gitf0cd09a
- hyperkube.server: don't parse args for any command

* Fri Mar 04 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.14.alpha6.gitf0cd09a
- Disable extensions/v1beta1 implicitly

* Tue Mar 01 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.13.alpha6.gitf0cd09a
- Hyperkube checks flags of individual commands/servers even if it does not define their flags.
  Thus resulting in 'uknown shorthand flag' error

* Mon Feb 29 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.12.alpha6.gitf0cd09a
- Disable v1beta3
- hyperkube-kubectl-dont shift os.Args

* Fri Feb 26 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.11.alpha6.gitf0cd09a
- add kube- prefix to controller-manager, proxy and scheduler

* Fri Feb 26 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.10.alpha6.gitf0cd09a
- Hardlink kube-controller-manager, kuber-scheduler, kubectl, kubelet and kube-proxy into hyperkube
- Keep kube-apiserver binary as it is (it has different permission and capabilities)

* Thu Feb 25 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.9.alpha6.gitf0cd09a
- Fix Content-Type of docker client response
  resolves: #1311861

* Mon Feb 22 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.2.0-0.8.alpha6.gitf0cd09a
- https://fedoraproject.org/wiki/Changes/golang1.6

* Mon Feb 22 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.7.alpha6.git4c8e6f4
- Bump to origin 1.1.3
  kube-version-change command replaced with kubectl convert (check out docs/admin/cluster-management.md)
  related: 1295066

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 1.2.0-0.6.alpha1.git4c8e6f4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Thu Jan 21 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.5.alpha1.git4c8e6f4
- Bump to upstream e1d9873c1d5711b83fd3dd7eefe83a88ceb92c08
  related: #1291860

* Thu Jan 07 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.4.alpha1.git4c8e6f4
- Move definition of all version, git and commit macros at one place
  resolves: #1291860

* Fri Jan 01 2016 jchaloup <jchaloup@redhat.com> - 1.2.0-0.3.alpha1.git4c8e6f4
- Bump to upstream bf56e235826baded1772fb340266b8419c3e8f30
  Rebase to origin's "v1.1.0.1 - Security Update to v1.1" release
  resolves: #1295066

* Thu Nov 26 2015 jchaloup <jchaloup@redhat.com> - 1.2.0-0.2.alpha1.git4c8e6f4
- Bump to origin upstream a41c9ff38d52fd508481c3c2bac13d52871fde02
- Build kubernetes from origin's Godeps using hack/build-go.sh
  origin's Godeps = kubernetes upstream + additional patches

* Tue Oct 20 2015 jchaloup <jchaloup@redhat.com> - 1.2.0-0.1.alpha1.git4c8e6f4
- Bump to upstream 403de3874fba420fd096f2329b45fe2f5ae97e46
  related: #1211266

* Wed Oct 14 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.41.alpha1.gite9a6ef1
- Bump to origin upstream e9a6ef1cd4c29d45730289a497d18b19d7ba450d
  related: #1211266

* Fri Oct 09 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.40.alpha1.git5f38cb0
- Add missing short option for --server of kubectl
- Update unit-test-subpackage (only test-cmd.sh atm)
  related: #1211266

* Fri Oct 09 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.39.alpha1.git5f38cb0
- Add normalization of flags 
  related: #1211266

* Fri Oct 02 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.38.alpha1.git5f38cb0
- Restore unit-test subpackage (not yet tested)
  related: #1211266

* Wed Sep 30 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.37.alpha1.git5f38cb0
- Do not unset default cluster, otherwise k8s ends with error when no cluster set
  related: #1211266

* Wed Sep 30 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.36.alpha0.git5f38cb0
- Bump to o4n 5f38cb0e98c9e854cafba9c7f98dafd51e955ad8
  related: #1211266

* Tue Sep 29 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.35.alpha1.git2695cdc
- Update git version of k8s and o4n, add macros
  related: #1211266

* Tue Sep 29 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.34.alpha1.git2695cdc
- Built k8s from o4n tarball
- Bump to upstream 2695cdcd29a8f11ef60278758e11f4817daf3c7c
  related: #1211266

* Tue Sep 22 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.33.alpha1.git09cf38e
- Bump to upstream 09cf38e9a80327e2d41654db277d00f19e2c84d0
  related: #1211266

* Thu Sep 17 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.32.alpha1.git400e685
- Bump to upstream 400e6856b082ecf4b295568acda68d630fc000f1
  related: #1211266

* Wed Sep 16 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.31.gitd549fc4
- Bump to upstream d549fc400ac3e5901bd089b40168e1e6fb17341d
  related: #1211266

* Tue Sep 15 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.30.gitc9570e3
- Bump to upstream c9570e34d03c6700d83f796c0125d17c5064e57d
  related: #1211266

* Mon Sep 14 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.29.git86b4e77
- Bump to upstream 86b4e777e1947c1bc00e422306a3ca74cbd54dbe
  related: #1211266

* Thu Sep 10 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.28.gitf867ba3
- Bump to upstream f867ba3ba13e3dad422efd21c74f52b9762de37e
  related: #1211266

* Wed Sep 09 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.27.git0f4fa4e
- Bump to upstream 0f4fa4ed25ae9a9d1824fe55aeefb4d4ebfecdfd
  related: #1211266

* Tue Sep 08 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.26.git196f58b
- Bump to upstream 196f58b9cb25a2222c7f9aacd624737910b03acb
  related: #1211266

* Mon Sep 07 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.25.git96e0ed5
- Bump to upstream 96e0ed5749608d4cc32f61b3674deb04c8fa90ad
  related: #1211266

* Sat Sep 05 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.24.git2e2def3
- Bump to upstream 2e2def36a904fe9a197da5fc70e433e2e884442f
  related: #1211266

* Fri Sep 04 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.23.gite724a52
- Bump to upstream e724a5210adf717f62a72162621ace1e08730c75
  related: #1211266

* Thu Sep 03 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.22.gitb6f2f39
- Bump to upstream b6f2f396baec5105ff928cf61903c2c368259b21
  related: #1211266

* Wed Sep 02 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.21.gitb4a3698
- Bump to upstream b4a3698faed81410468eccf9f328ca6df3d0cca3
  related: #1211266

* Tue Sep 01 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.20.git2f9652c
- Bump to upstream 2f9652c7f1d4b8f333c0b5c8c1270db83b913436
  related: #1211266

* Mon Aug 31 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.19.git66a644b
- Bump to upstream 66a644b275ede9ddb98eb3f76e8d1840cafc2147
  related: #1211266

* Thu Aug 27 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.18.gitab73849
- Bump to upstream ab7384943748312f5e9294f42d42ed3983c7c96c
  related: #1211266

* Wed Aug 26 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.17.git00e3442
- Bump to upstream 00e34429e0242323ed34347cf0ab65b3d62b21f7
  related: #1211266

* Tue Aug 25 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.16.gita945785
- Bump to upstream a945785409d5b68f3a2721d2209300edb5abf1ce
  related: #1211266

* Mon Aug 24 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.15.git5fe7029
- Bump to upstream 5fe7029e688e1e5873a0b95a622edda5b5156d2b
  related: #1211266

* Fri Aug 21 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.14.gitb6f18c7
- Bump to upstream b6f18c7ce08714c8d4f6019463879a164a41750e
  related: #1211266

* Thu Aug 20 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.13.git44fa48e
- Bump to upstream 44fa48e5af44d3e988fa943d96a2de732d8cc666
  related: #1211266

* Wed Aug 19 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.12.gitb5a4a54
- Bump to upstream b5a4a548df0cffb99bdcc3b9b9e48d4025d0541c
  related: #1211266

* Tue Aug 18 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.11.git919c7e9
- Bump to upstream 919c7e94e23d2dcd5bdd96896e0a7990f9ae3338
  related: #1211266

* Tue Aug 18 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.10.git280b66c
- Bump to upstream 280b66c9012c21e253acd4e730f8684c39ca08ec
  related: #1211266

* Mon Aug 17 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.9.git081d9c6
- Bump to upstream 081d9c64d25c20ec16035036536511811118173d
  related: #1211266

* Fri Aug 14 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.8.git8dcbeba
- Bump to upstream 8dcbebae5ef6a7191d9dfb65c68833c6852a21ad
  related: #1211266

* Thu Aug 13 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.7.git968cbbe
- Bump to upstream 968cbbee5d4964bd916ba379904c469abb53d623
  related: #1211266

* Wed Aug 12 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.6.gitc91950f
- Bump to upstream c91950f01cb14ad47486dfcd2fdfb4be3ee7f36b
  related: #1211266

* Tue Aug 11 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.5.gite44c8e6
- Bump to upstream e44c8e6661c931f7fd434911b0d3bca140e1df3a
  related: #1211266

* Mon Aug 10 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.4.git2bfa9a1
- Bump to upstream 2bfa9a1f98147cfdc2e9f4cf50e2c430518d91eb
  related: #1243827

* Thu Aug 06 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.3.git4c42e13
- Bump to upstream 4c42e1302d3b351f3cb6074d32aa420bbd45e07d
- Change import path prefix to k8s.io/kubernetes
  related: #1243827

* Wed Aug 05 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.2.git159ba48
- Bump to upstream 159ba489329e9f6ce422541e13f97e1166090ec8
  related: #1243827

* Sat Aug 01 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.1.git6129d3d
- Bump to upstream 6129d3d4eb80714286650818081a64ce2699afed
  related: #1243827

* Fri Jul 31 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.18.gitff058a1
- Bump to upstream ff058a1afeb63474f7a35805941f3b07c27aae0f
  related: #1243827

* Thu Jul 30 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.17.git769230e
- Bump to upstream 769230e735993bb0bf924279a40593c147c9a6ab
  related: #1243827

* Wed Jul 29 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.16.gitdde7222
- Bump to upstream dde72229dc9cbbdacfb2e44b22d9d5b357027020
  related: #1243827

* Tue Jul 28 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.15.gitc5bffaa
- Bump to upstream c5bffaaf3166513da6259c44a5d1ba8e86bea5ce
  related: #1243827

* Sat Jul 25 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.14.git5bd82ff
- Bump to upstream 5bd82ffe6da8f4e72e71b362635e558bfc412106
  related: #1243827

* Fri Jul 24 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.13.git291acd1
- Bump to upstream 291acd1a09ac836ec7524b060a19a6498d9878dd
  related: #1243827

* Thu Jul 23 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.12.gitfbed349
- Bump to upstream fbed3492bfa09e59b1c423fdd7c1ecad333a06ef
  related: #1243827

* Tue Jul 21 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.11.gitfbc85e9
- Add runtime dependency of kubernetes-node on socat (so kubectl port-forward works on AH)

* Tue Jul 21 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.10.gitfbc85e9
- Update the build script for go1.5 as well
- Bump to upstream fbc85e9838f25547be94fbffeeb92a756d908ca0
  related: #1243827

* Mon Jul 20 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.9.git2d88675
- Bump to upstream 2d88675f2203d316d4bac312c7ccad12991b56c2
- Change KUBE_ETCD_SERVERS to listen on 2379 ports instead of 4001
  resolves: #1243827
- Add kubernetes-client to provide kubectl command
  resolves: #1241469

* Mon Jul 20 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.8.gitb2dafda
- Fix dependency and tests for go-1.5
- with_debug off as the builds ends with error "ELFRESERVE too small: ..."

* Sat Jul 18 2015 Eric Paris <eparis@redhat.com> - 1.0.0-0.7.gitb2dafda
- Update apiserver binary gid

* Fri Jul 17 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.6.gitb2dafda
- Bump to upstream b2dafdaef5aceafad503ab56254b60f80da9e980
  related: #1211266

* Thu Jul 16 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.5.git596a8a4
- Bump to upstream 596a8a40d12498b5335140f50753980bfaea4f6b
  related: #1211266

* Wed Jul 15 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.4.git6ba532b
- Bump to upstream 6ba532b218cb5f5ea3f0e8dce5395182f388536c
  related: #1211266

* Tue Jul 14 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.3.gitc616182
- Bump to upstream c6161824db3784e6156131307a5e94647e5557fd
  related: #1211266

* Mon Jul 13 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.2.git2c27b1f
- Bump to upstream 2c27b1fa64f4e70f04575d1b217494f49332390e
  related: #1211266

* Sat Jul 11 2015 jchaloup <jchaloup@redhat.com> - 1.0.0-0.1.git1b37059
- Bump to upstream 1b370599ccf271741e657335c4943cb8c7dba28b
  related: #1211266

* Fri Jul 10 2015 jchaloup <jchaloup@redhat.com> - 0.21.1-0.2.gitccc4cfc
- Bump to upstream ccc4cfc7e11e0f127ac1cea045017dd799be3c63
  related: #1211266

* Thu Jul 09 2015 jchaloup <jchaloup@redhat.com> - 0.21.1-0.1.git41f8907
- Update generating of man pages from md (add genmanpages.sh)
- Bump to upstream 41f89075396329cd46c58495c7d3f7e13adcaa96
  related: #1211266

* Wed Jul 08 2015 jchaloup <jchaloup@redhat.com> - 0.20.2-0.5.git77be29e
- Bump to upstream 77be29e3da71f0a136b6aa4048b2f0575c2598e4
  related: #1211266

* Tue Jul 07 2015 jchaloup <jchaloup@redhat.com> - 0.20.2-0.4.git639a7da
- Bump to upstream 639a7dac50a331414cc6c47083323388da0d8756
  related: #1211266

* Mon Jul 06 2015 jchaloup <jchaloup@redhat.com> - 0.20.2-0.3.gitbb6f2f7
- Bump to upstream bb6f2f7ad90596d624d84cc691eec0f518e90cc8
  related: #1211266

* Fri Jul 03 2015 jchaloup <jchaloup@redhat.com> - 0.20.2-0.2.git974377b
- Bump to upstream 974377b3064ac59b6e5694bfa568d67128026171
  related: #1211266

* Thu Jul 02 2015 jchaloup <jchaloup@redhat.com> - 0.20.2-0.1.gitef41ceb
- Bump to upstream ef41ceb3e477ceada84c5522f429f02ab0f5948e
  related: #1211266

* Tue Jun 30 2015 jchaloup <jchaloup@redhat.com> - 0.20.0-0.3.git835eded
- Bump to upstream 835eded2943dfcf13a89518715e4be842a6a3ac0
- Generate missing man pages
  related: #1211266

* Mon Jun 29 2015 jchaloup <jchaloup@redhat.com> - 0.20.0-0.2.git1c0b765
- Bump to upstream 1c0b765df6dabfe9bd0e20489ed3bd18e6b3bda8
  Comment out missing man pages
  related: #1211266

* Fri Jun 26 2015 jchaloup <jchaloup@redhat.com> - 0.20.0-0.1.git8ebd896
- Bump to upstream 8ebd896351513d446d56bc5785c070d2909226a3
  related: #1211266

* Fri Jun 26 2015 jchaloup <jchaloup@redhat.com> - 0.19.3-0.6.git712f303
- Bump to upstream 712f303350b35e70a573f3cb19193c8ec7ee7544
  related: #1211266

* Thu Jun 25 2015 jchaloup <jchaloup@redhat.com> - 0.19.3-0.5.git2803b86
- Bump to upstream 2803b86a42bf187afa816a7ce14fec754cc2af51
  related: #1211266

* Wed Jun 24 2015 Eric Paris <eparis@redhat.com> - 0.19.3-0.4.git5b4dc4e
- Set CAP_NET_BIND_SERVICE on the kube-apiserver so it can use 443

* Wed Jun 24 2015 jchaloup <jchaloup@redhat.com> - 0.19.3-0.3.git5b4dc4e
- Bump to upstream 5b4dc4edaa14e1ab4e3baa19df0388fa54dab344
  pkg/cloudprovider/* packages does not conform to golang language specification
  related: #1211266

* Tue Jun 23 2015 jchaloup <jchaloup@redhat.com> - 0.19.3-0.2.gita2ce3ea
- Bump to upstream a2ce3ea5293553b1fe0db3cbc6d53bdafe061d79
  related: #1211266

* Mon Jun 22 2015 jchaloup <jchaloup@redhat.com> - 0.19.1-0.1.gitff0546d
- Bump to upstream ff0546da4fc23598de59db9f747c535545036463
  related: #1211266

* Fri Jun 19 2015 jchaloup <jchaloup@redhat.com> - 0.19.0-0.7.gitb2e9fed
- Bump to upstream b2e9fed3490274509506285bdba309c50afb5c39
  related: #1211266

* Thu Jun 18 2015 jchaloup <jchaloup@redhat.com> - 0.19.0-0.6.gitf660940
- Bump to upstream f660940dceb3fe6ffb1b14ba495a47d91b5cd910
  related: #1211266

* Wed Jun 17 2015 jchaloup <jchaloup@redhat.com> - 0.19.0-0.5.git43889c6
- Bump to upstream 43889c612c4d396dcd8fbf3fbd217e106eaf5bce
  related: #1211266

* Tue Jun 16 2015 jchaloup <jchaloup@redhat.com> - 0.19.0-0.4.gita8269e3
- Bump to upstream a8269e38c9e2bf81ba18cd6420e2309745d5b0b9
  related: #1211266

* Sun Jun 14 2015 jchaloup <jchaloup@redhat.com> - 0.19.0-0.3.git5e5c1d1
- Bump to upstream 5e5c1d10976f2f26d356ca60ef7d0d715c9f00a2
  related: #1211266

* Fri Jun 12 2015 jchaloup <jchaloup@redhat.com> - 0.19.0-0.2.git0ca96c3
- Bump to upstream 0ca96c3ac8b47114169f3b716ae4521ed8c7657c
  related: #1211266

* Thu Jun 11 2015 jchaloup <jchaloup@redhat.com> - 0.19.0-0.1.git5a02fc0
- Bump to upstream 5a02fc07d8a943132b9e68fe7169778253318487
  related: #1211266

* Wed Jun 10 2015 jchaloup <jchaloup@redhat.com> - 0.18.2-0.3.git0dfb681
- Bump to upstream 0dfb681ba5d5dba535895ace9d650667904b5df7
  related: #1211266

* Tue Jun 09 2015 jchaloup <jchaloup@redhat.com> - 0.18.2-0.2.gitb68e08f
- golang-cover is not needed

* Tue Jun 09 2015 jchaloup <jchaloup@redhat.com> - 0.18.2-0.1.gitb68e08f
- Bump to upstream b68e08f55f5ae566c4ea3905d0993a8735d6d34f
  related: #1211266

* Sat Jun 06 2015 jchaloup <jchaloup@redhat.com> - 0.18.1-0.3.git0f1c4c2
- Bump to upstream 0f1c4c25c344f70c3592040b2ef092ccdce0244f
  related: #1211266

* Fri Jun 05 2015 jchaloup <jchaloup@redhat.com> - 0.18.1-0.2.git7309e1f
- Bump to upstream 7309e1f707ea5dd08c51f803037d7d22c20e2b92
  related: #1211266

* Thu Jun 04 2015 jchaloup <jchaloup@redhat.com> - 0.18.1-0.1.gita161edb
- Bump to upstream a161edb3960c01ff6e14813858c2eeb85910009b
  related: #1211266

* Wed Jun 03 2015 jchaloup <jchaloup@redhat.com> - 0.18.0-0.3.gitb5a91bd
- Bump to upstream b5a91bda103ed2459f933959241a2b57331747ba
- Don't run %%check section (kept only for local run). Tests are now handled via CI.
  related: #1211266

* Tue Jun 02 2015 jchaloup <jchaloup@redhat.com> - 0.18.0-0.2.git5520386
- Bump to upstream 5520386b180d3ddc4fa7b7dfe6f52642cc0c25f3
  related: #1211266

* Mon Jun 01 2015 jchaloup <jchaloup@redhat.com> - 0.18.0-0.1.git0bb78fe
- Bump to upstream 0bb78fe6c53ce38198cc3805c78308cdd4805ac8
  related: #1211266

* Fri May 29 2015 jchaloup <jchaloup@redhat.com> - 0.17.1-6
- Bump to upstream ed4898d98c46869e9cbdb44186dfdeda9ff80cc2
  related: #1211266

* Thu May 28 2015 jchaloup <jchaloup@redhat.com> - 0.17.1-5
- Bump to upstream 6fa2777e26559fc008eacac83eb165d25bd9a7de
  related: #1211266

* Tue May 26 2015 jchaloup <jchaloup@redhat.com> - 0.17.1-4
- Bump to upstream 01fcb58673001e56c69e128ab57e0c3f701aeea5
  related: #1211266

* Mon May 25 2015 jchaloup <jchaloup@redhat.com> - 0.17.1-3
- Decompose package into master and node subpackage.
  Thanks to Avesh for testing and patience.
  related: #1211266

* Mon May 25 2015 jchaloup <jchaloup@redhat.com> - 0.17.1-2
- Bump to upstream cf7b0bdc2a41d38613ac7f8eeea91cae23553fa2
  related: #1211266

* Fri May 22 2015 jchaloup <jchaloup@redhat.com> - 0.17.1-1
- Bump to upstream d9d12fd3f7036c92606fc3ba9046b365212fcd70
  related: #1211266

* Wed May 20 2015 jchaloup <jchaloup@redhat.com> - 0.17.0-12
- Bump to upstream a76bdd97100c66a46e2b49288540dcec58a954c4
  related: #1211266

* Tue May 19 2015 jchaloup <jchaloup@redhat.com> - 0.17.0-11
- Bump to upstream 10339d72b66a31592f73797a9983e7c207481b22
  related: #1211266

* Mon May 18 2015 jchaloup <jchaloup@redhat.com> - 0.17.0-10
- Bump to upstream efb42b302d871f7217394205d84e5ae82335d786
  related: #1211266

* Sat May 16 2015 jchaloup <jchaloup@redhat.com> - 0.17.0-9
- Bump to upstream d51e131726b925e7088b90915e99042459b628e0
  related: #1211266

* Fri May 15 2015 jchaloup <jchaloup@redhat.com> - 0.17.0-8
- Bump to upstream 1ee33ac481a14db7b90e3bbac8cec4ceea822bfb
  related: #1211266

* Fri May 15 2015 jchaloup <jchaloup@redhat.com> - 0.17.0-7
- Bump to upstream d3c6fb0d6a13c0177dcd67556d72963c959234ea
  related: #1211266

* Fri May 15 2015 jchaloup <jchaloup@redhat.com> - 0.17.0-6
- Bump to upstream f57f31783089f41c0bdca8cb87a1001ca94e1a45
  related: #1211266

* Thu May 14 2015 jchaloup <jchaloup@redhat.com> - 0.17.0-5
- Bump to upstream c90d381d0d5cf8ab7b8412106f5a6991d7e13c7d
  related: #1211266

* Thu May 14 2015 jchaloup <jchaloup@redhat.com> - 0.17.0-4
- Bump to upstream 5010b2dde0f9b9eb820fe047e3b34bc9fa6324de
- Add debug info
  related: #1211266

* Wed May 13 2015 jchaloup <jchaloup@redhat.com> - 0.17.0-3
- Bump to upstream ec19d41b63f5fe7b2c939e7738a41c0fbe65d796
  related: #1211266

* Tue May 12 2015 jchaloup <jchaloup@redhat.com> - 0.17.0-2
- Provide /usr/bin/kube-version-change binary
  related: #1211266

* Tue May 12 2015 jchaloup <jchaloup@redhat.com> - 0.17.0-1
- Bump to upstream 962f10ee580eea30e5f4ea725c4e9e3743408a58
  related: #1211266

* Mon May 11 2015 jchaloup <jchaloup@redhat.com> - 0.16.2-7
- Bump to upstream 63182318c5876b94ac9b264d1224813b2b2ab541
  related: #1211266

* Fri May 08 2015 jchaloup <jchaloup@redhat.com> - 0.16.2-6
- Bump to upstream d136728df7e2694df9e082902f6239c11b0f2b00
- Add NetworkManager as dependency for /etc/resolv.conf
  related: #1211266

* Thu May 07 2015 jchaloup <jchaloup@redhat.com> - 0.16.2-5
- Bump to upstream ca0f678b9a0a6dc795ac7a595350d0dbe9d0ac3b
  related: #1211266

* Wed May 06 2015 jchaloup <jchaloup@redhat.com> - 0.16.2-4
- Add docs to kubernetes-unit-test
  related: #1211266

* Wed May 06 2015 jchaloup <jchaloup@redhat.com> - 0.16.2-3
- Bump to upstream 3a24c0e898cb3060d7905af6df275a3be562451d
  related: #1211266

* Tue May 05 2015 jchaloup <jchaloup@redhat.com> - 0.16.2-2
- Add api and README.md to kubernetes-unit-test
  related: #1211266

* Tue May 05 2015 jchaloup <jchaloup@redhat.com> - 0.16.2-1
- Bump to upstream 72048a824ca16c3921354197953fabecede5af47
  related: #1211266

* Mon May 04 2015 jchaloup <jchaloup@redhat.com> - 0.16.1-2
- Bump to upstream 1dcd80cdf3f00409d55cea1ef0e7faef0ae1d656
  related: #1211266

* Sun May 03 2015 jchaloup <jchaloup@redhat.com> - 0.16.1-1
- Bump to upstream 86751e8c90a3c0e852afb78d26cb6ba8cdbc37ba
  related: #1211266

* Fri May 01 2015 jchaloup <jchaloup@redhat.com> - 0.16.0-2
- Bump to upstream 72708d74b9801989ddbdc8403fc5ba4aafb7c1ef
  related: #1211266

* Wed Apr 29 2015 jchaloup <jchaloup@redhat.com> - 0.16.0-1
- Bump to upstream 7dcce2eeb7f28643d599c8b6a244523670d17c93
  related: #1211266

* Tue Apr 28 2015 jchaloup <jchaloup@redhat.com> - 0.15.0-10
- Add unit-test subpackage
  related: #1211266

* Tue Apr 28 2015 jchaloup <jchaloup@redhat.com> - 0.15.0-9
- Bump to upstream 99fc906f78cd2bcb08536c262867fa6803f816d5
  related: #1211266

* Mon Apr 27 2015 jchaloup <jchaloup@redhat.com> - 0.15.0-8
- Bump to upstream 051dd96c542799dfab39184d2a7c8bacf9e88d85
  related: #1211266

* Fri Apr 24 2015 jchaloup <jchaloup@redhat.com> - 0.15.0-7
- Bump to upstream 9f753c2592481a226d72cea91648db8fb97f0da8
  related: #1211266

* Thu Apr 23 2015 jchaloup <jchaloup@redhat.com> - 0.15.0-6
- Bump to upstream cf824ae5e07965ba0b4b15ee88e08e2679f36978
  related: #1211266

* Tue Apr 21 2015 jchaloup <jchaloup@redhat.com> - 0.15.0-5
- Bump to upstream 21788d8e6606038a0a465c97f5240b4e66970fbb
  related: #1211266

* Mon Apr 20 2015 jchaloup <jchaloup@redhat.com> - 0.15.0-4
- Bump to upstream eb1ea269954da2ce557f3305fa88d42e3ade7975
  related: #1211266

* Fri Apr 17 2015 jchaloup <jchaloup@redhat.com> - 0.15.0-3
- Obsolete cadvisor as it is integrated in kubelet
  related: #1211266

* Wed Apr 15 2015 jchaloup <jchaloup@redhat.com> - 0.15.0-0.2.git0ea87e4
- Bump to upstream 0ea87e486407298dc1e3126c47f4076b9022fb09
  related: #1211266

* Tue Apr 14 2015 jchaloup <jchaloup@redhat.com> - 0.15.0-0.1.gitd02139d
- Bump to upstream d02139d2b454ecc5730cc535d415c1963a7fb2aa
  related: #1211266

* Sun Apr 12 2015 jchaloup <jchaloup@redhat.com> - 0.14.2-0.2.gitd577db9
- Bump to upstream d577db99873cbf04b8e17b78f17ec8f3a27eca30

* Wed Apr 08 2015 jchaloup <jchaloup@redhat.com> - 0.14.2-0.1.git2719194
- Bump to upstream 2719194154ffd38fd1613699a9dd10a00909957e
  Use etcd-2.0.8 and higher

* Tue Apr 07 2015 jchaloup <jchaloup@redhat.com> - 0.14.1-0.2.gitd2f4734
- Bump to upstream d2f473465738e6b6f7935aa704319577f5e890ba

* Thu Apr 02 2015 jchaloup <jchaloup@redhat.com> - 0.14.1-0.1.gita94ffc8
- Bump to upstream a94ffc8625beb5e2a39edb01edc839cb8e59c444

* Wed Apr 01 2015 jchaloup <jchaloup@redhat.com> - 0.14.0-0.2.git8168344
- Bump to upstream 81683441b96537d4b51d146e39929b7003401cd5

* Tue Mar 31 2015 jchaloup <jchaloup@redhat.com> - 0.14.0-0.1.git9ed8761
- Bump to upstream 9ed87612d07f75143ac96ad90ff1ff68f13a2c67
- Remove [B]R from devel branch until the package has stable API

* Mon Mar 30 2015 jchaloup <jchaloup@redhat.com> - 0.13.2-0.6.git8a7a127
- Bump to upstream 8a7a127352263439e22253a58628d37a93fdaeb2

* Fri Mar 27 2015 jchaloup <jchaloup@redhat.com> - 0.13.2-0.5.git8d94c43
- Bump to upstream 8d94c43e705824f23791b66ad5de4ea095d5bb32
  resolves: #1205362

* Wed Mar 25 2015 jchaloup <jchaloup@redhat.com> - 0.13.2-0.4.git455fe82
- Bump to upstream 455fe8235be8fd9ba0ce21bf4f50a69d42e18693

* Mon Mar 23 2015 jchaloup <jchaloup@redhat.com> - 0.13.2-0.3.gitef75888
- Remove runtime dependency on etcd
  resolves: #1202923

* Sun Mar 22 2015 jchaloup <jchaloup@redhat.com> - 0.13.2-0.2.gitef75888
- Bump to upstream ef758881d108bb53a128126c503689104d17f477

* Fri Mar 20 2015 jchaloup <jchaloup@redhat.com> - 0.13.2-0.1.gita8f2cee
- Bump to upstream a8f2cee8c5418676ee33a311fad57d6821d3d29a

* Fri Mar 13 2015 jchaloup <jchaloup@redhat.com> - 0.12.0-0.9.git53b25a7
- Bump to upstream 53b25a7890e31bdec6f2a95b32200d6cc27ae2ca
  fix kube-proxy.service and kubelet
  resolves: #1200919 #1200924

* Fri Mar 13 2015 jchaloup <jchaloup@redhat.com> - 0.12.0-0.8.git39dceb1
- Bump to upstream 39dceb13a511a83963a766a439cb386d10764310

* Thu Mar 12 2015 Eric Paris <eparis@redhat.com> - 0.12.0-0.7.gita3fd0a9
- Move from /etc/tmpfiles.d to %%{_tmpfilesdir}
  resolves: #1200969

* Thu Mar 12 2015 jchaloup <jchaloup@redhat.com> - 0.12.0-0.6.gita3fd0a9
- Place contrib/init/systemd/tmpfiles.d/kubernetes.conf to /etc/tmpfiles.d/kubernetes.conf

* Thu Mar 12 2015 jchaloup <jchaloup@redhat.com> - 0.12.0-0.5.gita3fd0a9
- Bump to upstream a3fd0a9fd516bb6033f32196ae97aaecf8c096b1

* Tue Mar 10 2015 jchaloup <jchaloup@redhat.com> - 0.12.0-0.4.gita4d871a
- Bump to upstream a4d871a10086436557f804930812f2566c9d4d39

* Fri Mar 06 2015 jchaloup <jchaloup@redhat.com> - 0.12.0-0.3.git2700871
- Bump to upstream 2700871b049d5498167671cea6de8317099ad406

* Thu Mar 05 2015 jchaloup <jchaloup@redhat.com> - 0.12.0-0.2.git8b627f5
- Bump to upstream 8b627f516fd3e4f62da90d401ceb3d38de6f8077

* Tue Mar 03 2015 jchaloup <jchaloup@redhat.com> - 0.12.0-0.1.gitecca426
- Bump to upstream ecca42643b91a7117de8cd385b64e6bafecefd65

* Mon Mar 02 2015 jchaloup <jchaloup@redhat.com> - 0.11.0-0.5.git6c5b390
- Bump to upstream 6c5b390160856cd8334043344ef6e08568b0a5c9

* Sat Feb 28 2015 jchaloup <jchaloup@redhat.com> - 0.11.0-0.4.git0fec31a
- Bump to upstream 0fec31a11edff14715a1efb27f77262a7c3770f4

* Fri Feb 27 2015 jchaloup <jchaloup@redhat.com> - 0.11.0-0.3.git08402d7
- Bump to upstream 08402d798c8f207a2e093de5a670c5e8e673e2de

* Wed Feb 25 2015 jchaloup <jchaloup@redhat.com> - 0.11.0-0.2.git86434b4
- Bump to upstream 86434b4038ab87ac40219562ad420c3cc58c7c6b

* Tue Feb 24 2015 jchaloup <jchaloup@redhat.com> - 0.11.0-0.1.git754a2a8
- Bump to upstream 754a2a8305c812121c3845d8293efdd819b6a704
  turn off integration tests until "FAILED: unexpected endpoints:
  timed out waiting for the condition" problem is resolved
  Adding back devel subpackage ([B]R list outdated)

* Fri Feb 20 2015 jchaloup <jchaloup@redhat.com> - 0.10.1-0.3.git4c87805
- Bump to upstream 4c87805870b1b22e463c4bd711238ef68c77f0af

* Tue Feb 17 2015 jchaloup <jchaloup@redhat.com> - 0.10.1-0.2.git6f84bda
- Bump to upstream 6f84bdaba853872dbac69c84d3ab4b6964e85d8c

* Tue Feb 17 2015 jchaloup <jchaloup@redhat.com> - 0.10.1-0.1.git7d6130e
- Bump to upstream 7d6130edcdfabd7dd2e6a06fdc8fe5e333f07f5c

* Sat Feb 07 2015 jchaloup <jchaloup@redhat.com> - 0.9.1-0.7.gitc9c98ab
- Bump to upstream c9c98ab19eaa6f0b2ea17152c9a455338853f4d0
  Since some dependencies are broken, we can not build Kubernetes from Fedora deps.
  Switching to vendored source codes until Go draft is resolved

* Wed Feb 04 2015 jchaloup <jchaloup@redhat.com> - 0.9.1-0.6.git7f5ed54
- Bump to upstream 7f5ed541f794348ae6279414cf70523a4d5133cc

* Tue Feb 03 2015 jchaloup <jchaloup@redhat.com> - 0.9.1-0.5.git2ac6bbb
- Bump to upstream 2ac6bbb7eba7e69eac71bd9acd192cda97e67641

* Mon Feb 02 2015 jchaloup <jchaloup@redhat.com> - 0.9.1-0.4.gite335e2d
- Bump to upstream e335e2d3e26a9a58d3b189ccf41ceb3770d1bfa9

* Fri Jan 30 2015 jchaloup <jchaloup@redhat.com> - 0.9.1-0.3.git55793ac
- Bump to upstream 55793ac2066745f7243c666316499e1a8cf074f0

* Thu Jan 29 2015 jchaloup <jchaloup@redhat.com> - 0.9.1-0.2.gitca6de16
- Bump to upstream ca6de16df7762d4fc9b4ad44baa78d22e3f30742

* Tue Jan 27 2015 jchaloup <jchaloup@redhat.com> - 0.9.1-0.1.git3623a01
- Bump to upstream 3623a01bf0e90de6345147eef62894057fe04b29
- update tests for etcd-2.0

* Thu Jan 22 2015 jchaloup <jchaloup@redhat.com> - 0.8.2-571.gitb2f287c
+- Bump to upstream b2f287c259d856f4c08052a51cd7772c563aff77

* Thu Jan 22 2015 Eric Paris <eparis@redhat.com> - 0.8.2-570.gitb2f287c
- patch kubelet service file to use docker.service not docker.socket

* Wed Jan 21 2015 jchaloup <jchaloup@redhat.com> - 0.8.2-0.1.git5b04640
- Bump to upstream 5b046406a957a1e7eda7c0c86dd7a89e9c94fc5f

* Sun Jan 18 2015 jchaloup <jchaloup@redhat.com> - 0.8.0-126.0.git68298f0
- Add some missing dependencies
- Add devel subpackage

* Fri Jan 09 2015 Eric Paris <eparis@redhat.com> - 0.8.0-125.0.git68298f0
- Bump to upstream 68298f08a4980f95dfbf7b9f58bfec1808fb2670

* Tue Dec 16 2014 Eric Paris <eparis@redhat.com> - 0.7.0-18.0.git52e165a
- Bump to upstream 52e165a4fd720d1703ebc31bd6660e01334227b8

* Mon Dec 15 2014 Eric Paris <eparis@redhat.com> - 0.6-297.0.git5ef34bf
- Bump to upstream 5ef34bf52311901b997119cc49eff944c610081b

* Wed Dec 03 2014 Eric Paris <eparis@redhat.com>
- Replace patch to use old googlecode/go.net/ with BuildRequires on golang.org/x/net/

* Tue Dec 02 2014 Eric Paris <eparis@redhat.com> - 0.6-4.0.git993ef88
- Bump to upstream 993ef88eec9012b221f79abe8f2932ee97997d28

* Mon Dec 01 2014 Eric Paris <eparis@redhat.com> - 0.5-235.0.git6aabd98
- Bump to upstream 6aabd9804fb75764b70e9172774002d4febcae34

* Wed Nov 26 2014 Eric Paris <eparis@redhat.com> - 0.5-210.0.gitff1e9f4
- Bump to upstream ff1e9f4c191342c24974c030e82aceaff8ea9c24

* Tue Nov 25 2014 Eric Paris <eparis@redhat.com> - 0.5-174.0.git64e07f7
- Bump to upstream 64e07f7fe03d8692c685b09770c45f364967a119

* Mon Nov 24 2014 Eric Paris <eparis@redhat.com> - 0.5-125.0.git162e498
- Bump to upstream 162e4983b947d2f6f858ca7607869d70627f5dff

* Fri Nov 21 2014 Eric Paris <eparis@redhat.com> - 0.5-105.0.git3f74a1e
- Bump to upstream 3f74a1e9f56b3c3502762930c0c551ccab0557ea

* Thu Nov 20 2014 Eric Paris <eparis@redhat.com> - 0.5-65.0.gitc6158b8
- Bump to upstream c6158b8aa9c40fbf1732650a8611429536466b21
- include go-restful build requirement

* Tue Nov 18 2014 Eric Paris <eparis@redhat.com> - 0.5-14.0.gitdf0981b
- Bump to upstream df0981bc01c5782ad30fc45cb6f510f365737fc1

* Tue Nov 11 2014 Eric Paris <eparis@redhat.com> - 0.4-680.0.git30fcf24
- Bump to upstream 30fcf241312f6d0767c7d9305b4c462f1655f790

* Mon Nov 10 2014 Eric Paris <eparis@redhat.com> - 0.4-633.0.git6c70227
- Bump to upstream 6c70227a2eccc23966d32ea6d558ee05df46e400

* Fri Nov 07 2014 Eric Paris <eparis@redhat.com> - 0.4-595.0.gitb695650
- Bump to upstream b6956506fa2682afa93770a58ea8c7ba4b4caec1

* Thu Nov 06 2014 Eric Paris <eparis@redhat.com> - 0.4-567.0.git3b1ef73
- Bump to upstream 3b1ef739d1fb32a822a22216fb965e22cdd28e7f

* Thu Nov 06 2014 Eric Paris <eparis@redhat.com> - 0.4-561.0.git06633bf
- Bump to upstream 06633bf4cdc1ebd4fc848f85025e14a794b017b4
- Make spec file more RHEL/CentOS friendly

* Tue Nov 04 2014 Eric Paris <eparis@redhat.com - 0.4-510.0.git5a649f2
- Bump to upstream 5a649f2b9360a756fc8124897d3453a5fa9473a6

* Mon Nov 03 2014 Eric Paris <eparis@redhat.com - 0.4-477.0.gita4abafe
- Bump to upstream a4abafea02babc529c9b5b9c825ba0bb3eec74c6

* Mon Nov 03 2014 Eric Paris <eparis@redhat.com - 0.4-453.0.git808be2d
- Bump to upstream 808be2d13b7bf14a3cf6985bc7c9d02f48a3d1e0
- Includes upstream change to remove --machines from the APIServer
- Port to new build system
- Start running %%check tests again

* Fri Oct 31 2014 Eric Paris <eparis@redhat.com - 0.4+-426.0.gita18cdac
- Bump to upstream a18cdac616962a2c486feb22afa3538fc3cf3a3a

* Thu Oct 30 2014 Eric Paris <eparis@redhat.com - 0.4+-397.0.git78df011
- Bump to upstream 78df01172af5cc132b7276afb668d31e91e61c11

* Wed Oct 29 2014 Eric Paris <eparis@redhat.com - 0.4+-0.9.git8e1d416
- Bump to upstream 8e1d41670783cb75cf0c5088f199961a7d8e05e5

* Tue Oct 28 2014 Eric Paris <eparis@redhat.com - 0.4-0.8.git1c61486
- Bump to upstream 1c61486ec343246a81f62b4297671217c9576df7

* Mon Oct 27 2014 Eric Paris <eparis@redhat.com - 0.4-0.7.gitdc7e3d6
- Bump to upstream dc7e3d6601a89e9017ca9db42c09fd0ecb36bb36

* Fri Oct 24 2014 Eric Paris <eparis@redhat.com - 0.4-0.6.gite46af6e
- Bump to upstream e46af6e37f6e6965a63edb8eb8f115ae8ef41482

* Thu Oct 23 2014 Eric Paris <eparis@redhat.com - 0.4-0.5.git77d2815
- Bump to upstream 77d2815b86e9581393d7de4379759c536df89edc

* Wed Oct 22 2014 Eric Paris <eparis@redhat.com - 0.4-0.4.git97dd730
- Bump to upstream 97dd7302ac2c2b9458a9348462a614ebf394b1ed
- Use upstream kubectl bash completion instead of in-repo
- Fix systemd_post and systemd_preun since we are using upstream service files

* Tue Oct 21 2014 Eric Paris <eparis@redhat.com - 0.4-0.3.gite868642
- Bump to upstream e8686429c4aa63fc73401259c8818da168a7b85e

* Mon Oct 20 2014 Eric Paris <eparis@redhat.com - 0.4-0.2.gitd5377e4
- Bump to upstream d5377e4a394b4fc6e3088634729b538eac124b1b
- Use in tree systemd unit and Environment files
- Include kubectl bash completion from outside tree

* Fri Oct 17 2014 Eric Paris <eparis@redhat.com - 0.4-0.1.gitb011263
- Bump to upstream b01126322b826a15db06f6eeefeeb56dc06db7af
- This is a major non backward compatible change.

* Thu Oct 16 2014 Eric Paris <eparis@redhat.com> - 0.4-0.0.git4452163
- rebase to v0.4
- include man pages

* Tue Oct 14 2014 jchaloup <jchaloup@redhat.com> - 0.3-0.3.git98ac8e1
- create /var/lib/kubelet
- Use bash completions from upstream
- Bump to upstream 98ac8e178fcf1627399d659889bcb5fe25abdca4
- all by Eric Paris

* Mon Sep 29 2014 Jan Chaloupka <jchaloup@redhat.com> - 0.3-0.2.git88fdb65
- replace * with coresponding files
- remove dependency on gcc

* Wed Sep 24 2014 Eric Paris <eparis@redhat.com - 0.3-0.1.git88fdb65
- Bump to upstream 88fdb659bc44cf2d1895c03f8838d36f4d890796

* Tue Sep 23 2014 Eric Paris <eparis@redhat.com - 0.3-0.0.gitbab5082
- Bump to upstream bab5082a852218bb65aaacb91bdf599f9dd1b3ac

* Fri Sep 19 2014 Eric Paris <eparis@redhat.com - 0.2-0.10.git06316f4
- Bump to upstream 06316f486127697d5c2f5f4c82963dec272926cf

* Thu Sep 18 2014 Eric Paris <eparis@redhat.com - 0.2-0.9.gitf7a5ec3
- Bump to upstream f7a5ec3c36bd40cc2216c1da331ab647733769dd

* Wed Sep 17 2014 Eric Paris <eparis@redhat.com - 0.2-0.8.gitac8ee45
- Try to intelligently determine the deps

* Wed Sep 17 2014 Eric Paris <eparis@redhat.com - 0.2-0.7.gitac8ee45
- Bump to upstream ac8ee45f4fc4579b3ed65faafa618de9c0f8fb26

* Mon Sep 15 2014 Eric Paris <eparis@redhat.com - 0.2-0.5.git24b5b7e
- Bump to upstream 24b5b7e8d3a8af1eecf4db40c204e3c15ae955ba

* Thu Sep 11 2014 Eric Paris <eparis@redhat.com - 0.2-0.3.gitcc7999c
- Bump to upstream cc7999c00a40df21bd3b5e85ecea3b817377b231

* Wed Sep 10 2014 Eric Paris <eparis@redhat.com - 0.2-0.2.git60d4770
- Add bash completions

* Wed Sep 10 2014 Eric Paris <eparis@redhat.com - 0.2-0.1.git60d4770
- Bump to upstream 60d4770127d22e51c53e74ca94c3639702924bd2

* Mon Sep 08 2014 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0.1-0.4.git6ebe69a
- prefer autosetup instead of setup (revert setup change in 0-0.3.git)
https://fedoraproject.org/wiki/Autosetup_packaging_draft
- revert version number to 0.1

* Mon Sep 08 2014 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0-0.3.git6ebe69a
- gopath defined in golang package already
- package owns /etc/kubernetes
- bash dependency implicit
- keep buildroot/$RPM_BUILD_ROOT macros consistent
- replace with macros wherever possible
- set version, release and source tarball prep as per
https://fedoraproject.org/wiki/Packaging:SourceURL#Github

* Mon Sep 08 2014 Eric Paris <eparis@redhat.com>
- make services restart automatically on error

* Sat Sep 06 2014 Eric Paris <eparis@redhat.com - 0.1-0.1.0.git6ebe69a8
- Bump to upstream 6ebe69a8751508c11d0db4dceb8ecab0c2c7314a

* Wed Aug 13 2014 Eric Paris <eparis@redhat.com>
- update to upstream
- redo build to use project scripts
- use project scripts in %%check
- rework deletion of third_party packages to easily detect changes
- run apiserver and controller-manager as non-root

* Mon Aug 11 2014 Adam Miller <maxamillion@redhat.com>
- update to upstream
- decouple the rest of third_party

* Thu Aug 7 2014 Eric Paris <eparis@redhat.com>
- update to head
- update package to include config files

* Wed Jul 16 2014 Colin Walters <walters@redhat.com>
- Initial package
