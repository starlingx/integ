%global with_debug 1
%global with_check 0

%if 0%{?with_debug}
%global _dwz_low_mem_die_limit 0
%else
%global debug_package   %{nil}
%endif

%if ! 0%{?gobuild:1}
%define gobuild(o:) go build -buildmode pie -compiler gc -tags="rpm_crashtraceback ${BUILDTAGS:-}" -ldflags "${LDFLAGS:-} -B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \\n') -extldflags '-Wl,-z,relro -Wl,-z,now -specs=/usr/lib/rpm/redhat/redhat-hardened-ld '" -a -v -x %{?**};
%endif

%global provider        github
%global provider_tld    com
%global project         containernetworking
%global repo            plugins
# https://github.com/containernetworking/plugins
%global provider_prefix %{provider}.%{provider_tld}/%{project}/%{repo}
%global import_path     %{provider_prefix}
%global commit          fe60fcddb897079746ec1523fd1837ab05b1e689
%global shortcommit     %(c=%{commit}; echo ${c:0:7})

Name: containernetworking-plugins
Version: 1.0.1
Release: 1%{?_tis_dist}.%{tis_patch_ver}
Summary: CNI network plugins
License: ASL 2.0
URL: https://%{provider_prefix}

Source0: %{project}-%{repo}-v%{version}.tar.gz
ExclusiveArch: aarch64 %{arm} ppc64le s390x x86_64 %{ix86}

%if 0%{?fedora}
BuildRequires: %{?go_compiler:compiler(go-compiler)}%{!?go_compiler:golang}
%else
#BuildRequires: go-toolset-1.10
BuildRequires:  %{?go_compiler:compiler(go-compiler)}%{!?go_compiler:golang}
BuildRequires: openssl-devel
%endif #fedora

Provides: containernetworking-cni = %{version}-%{release}

%description
The CNI (Container Network Interface) project consists of a specification
and libraries for writing plugins to configure network interfaces in Linux
containers, along with a number of supported plugins. CNI concerns itself
only with network connectivity of containers and removing allocated resources
when the container is deleted.

%{?enable_gotoolset110}

%prep
%autosetup -n %{project}-%{repo}-v%{version}
rm -rf plugins/main/windows

%build
export ORG_PATH="%{provider}.%{provider_tld}/%{project}"
export REPO_PATH="$ORG_PATH/%{repo}"

if [ ! -h gopath/src/${REPO_PATH} ]; then
   mkdir -p gopath/src/${ORG_PATH}
   ln -s ../../../.. gopath/src/${REPO_PATH} || exit 255
fi

export GOPATH=$(pwd)/gopath
mkdir -p $(pwd)/bin

echo "Building plugins"
export PLUGINS="plugins/meta/* plugins/main/* plugins/ipam/* plugins/sample"
for d in $PLUGINS; do
        if [ -d "$d" ]; then
                plugin="$(basename "$d")"
                echo "  $plugin"
                %gobuild -o "${PWD}/bin/$plugin" "$@" "$REPO_PATH"/$d
        fi
done

%install
install -d -p %{buildroot}/var/opt/cni/bin
install -p -m 0755 bin/* %{buildroot}/var/opt/cni/bin

%check
%if 0%{?with_check}

%if ! 0%{?gotest:1}
%global gotest go test
%endif

%gotest %{import_path}/libcni
%gotest %{import_path}/pkg/invoke
%gotest %{import_path}/pkg/ip
%gotest %{import_path}/pkg/ipam
%gotest %{import_path}/pkg/ns
%gotest %{import_path}/pkg/skel
%gotest %{import_path}/pkg/types
%gotest %{import_path}/pkg/types/020
%gotest %{import_path}/pkg/types/current
%gotest %{import_path}/pkg/utils
%gotest %{import_path}/pkg/utils/hwaddr
%gotest %{import_path}/pkg/version
%gotest %{import_path}/pkg/version/legacy_examples
%gotest %{import_path}/pkg/version/testhelpers
%gotest %{import_path}/plugins/ipam/dhcp
%gotest %{import_path}/plugins/ipam/host-local
%gotest %{import_path}/plugins/ipam/host-local/backend/allocator
%gotest %{import_path}/plugins/main/bridge
%gotest %{import_path}/plugins/main/ipvlan
%gotest %{import_path}/plugins/main/loopback
%gotest %{import_path}/plugins/main/macvlan
%gotest %{import_path}/plugins/main/ptp
%gotest %{import_path}/plugins/meta/flannel
%gotest %{import_path}/plugins/test/noop
%endif

#define license tag if not already defined
%{!?_licensedir:%global license %doc}

%files
%license LICENSE
%doc *.md
%dir /var/opt/cni/bin
/var/opt/cni/bin/*

%changelog
* Mon Jun 06 2022 Dan Voiculeasa <dan.voiculeasa@windriver.com>
- Update install directory to /var/opt/cni/bin.

* Thu Feb 17 2022 Steven Webster <steven.webster@windriver.com> - 1.0.1
- bump to v1.0.1

* Sun Aug 08 2021 Steven Webster <steven.webster@windriver.com>
- Support for compilation on StarlingX

* Fri Jun 07 2019 Lokesh Mandvekar <lsm5@redhat.com> - 0.8.1-1
- Resolves: #1717915 - bump to v0.8.1

* Tue May 14 2019 Lokesh Mandvekar <lsm5@redhat.com> - 0.8.0-1
- Resolves: #1709630 - rebase to v0.8.0

* Wed Mar 27 2019 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.7.5-2
- rebase

* Mon Jan 07 2019 Lokesh Mandvekar <lsm5@redhat.com> - 0.7.4-1
- Resolves: #1664009 - bump to v0.7.4
- remove unused devel and unit-test* packages
- update go build env

* Wed Nov 21 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.7.3-3
- buildrequires for centos

* Wed Oct 03 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.7.3-2
- rebase

* Wed Oct 03 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.7.1-2
- scl go toolset

* Mon Jul 23 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.7.1-1
- rebase

* Thu May 10 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.7.0-101
- rebase
- patches already upstream, removed

* Thu Apr 26 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.6.0-6
- Imported from Fedora
- Renamed CNI -> plugins

* Mon Apr  2 2018 Peter Robinson <pbrobinson@fedoraproject.org> 0.6.0-4
- Own the libexec cni directory

* Wed Feb 07 2018 Fedora Release Engineering <releng@fedoraproject.org> - 0.6.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Tue Jan 23 2018 Dan Williams <dcbw@redhat.com> - 0.6.0-2
- skip settling IPv4 addresses

* Mon Jan 08 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.6.0-1
- rebased to 7480240de9749f9a0a5c8614b17f1f03e0c06ab9

* Fri Oct 13 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0.5.2-7
- do not install to /opt (against Fedora Guidelines)

* Thu Aug 24 2017 Jan Chaloupka <jchaloup@redhat.com> - 0.5.2-6
- Enable devel subpackage

* Wed Aug 02 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.5.2-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Wed Jul 26 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.5.2-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Thu Jul 13 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0.5.2-3
- excludearch: ppc64 as it's not in goarches anymore
- re-enable s390x

* Fri Jun 30 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0.5.2-2
- upstream moved to github.com/containernetworking/plugins
- built commit dcf7368
- provides: containernetworking-plugins
- use vendored deps because they're a lot less of a PITA
- excludearch: s390x for now (rhbz#1466865)

* Mon Jun 12 2017 Timothy St. Clair <tstclair@heptio.com> - 0.5.2-1
- Update to 0.5.2
- Softlink to default /opt/cni/bin directories

* Sun May 07 2017 Timothy St. Clair <tstclair@heptio.com> - 0.5.1-1
- Initial package
