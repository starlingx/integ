# SPDX-License-Identifier: Apache-2.0
#
# Copyright (c) 2020 Wind River Systems, Inc.
#

# Use the same build parameters as the other CNI plugins from containernetworking-plugins
%if ! 0%{?gobuild:1}
%define gobuild(o:) go build -buildmode pie -compiler gc -tags="rpm_crashtraceback ${BUILDTAGS:-}" -ldflags "${LDFLAGS:-} -B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \\n') -extldflags '-Wl,-z,relro -Wl,-z,now -specs=/usr/lib/rpm/redhat/redhat-hardened-ld '" -a -v -x %{?**};
%endif

%global provider        github
%global provider_tld    com
%global project         k8snetworkplumbingwg
%global repo            bond-cni
# https://github.com/k8snetworkplumbingwg/bond-cni
%global provider_prefix %{provider}.%{provider_tld}/%{project}/%{repo}
%global import_path     %{provider_prefix}
%global commit          bff6422d7089d988dc1548e6abe0543601f6e1c7
%global shortcommit     %(c=%{commit}; echo ${c:0:7})

Name: bond-cni
Version: 1.0
Release: %{shortcommit}%{?_tis_dist}.%{tis_patch_ver}
Summary: Bond CNI network plugin
License: ASL 2.0
URL: https://%{provider_prefix}

Source0: %{repo}-%{commit}.tar.gz
Patch1: 0001-Add-explicit-vendor-module-dependencies.patch
ExclusiveArch: aarch64 %{arm} ppc64le s390x x86_64 %{ix86}

BuildRequires:  %{?go_compiler:compiler(go-compiler)}%{!?go_compiler:golang = 1.17.5}
Provides: bond-cni = %{version}-%{release}

%description
The Bond-CNI concerns itself only with providing network connectivity via
bonding of containers and removing any allocated resources when the container
is deleted.

%prep
%setup -n %{repo}-%{commit}
%patch1 -p1

%build
export ORG_PATH="%{provider}.%{provider_tld}/%{project}"
export REPO_PATH="$ORG_PATH/%{repo}"

if [ ! -h gopath/src/${REPO_PATH} ]; then
   mkdir -p gopath/src/${ORG_PATH}
   ln -s ../../../.. gopath/src/${REPO_PATH} || exit 255
fi

export GOPATH=$(pwd)/gopath
mkdir -p $(pwd)/bin

echo "Building bond-cni plugin"

%gobuild -o "${PWD}/bin/bond" "${PWD}/bond/"

%install
install -d -p %{buildroot}%{_libexecdir}/cni/
install -p -m 0755 bin/* %{buildroot}/%{_libexecdir}/cni

#define license tag if not already defined
%{!?_licensedir:%global license %doc}

%files
%license LICENSE
%doc *.md
%dir %{_libexecdir}/cni
%{_libexecdir}/cni/*

%changelog
* Fri Jan 21 2022 Steven Webster <steven.webster@windriver.com>
- Initial package, based on v1.0 + 14 additional commits.
