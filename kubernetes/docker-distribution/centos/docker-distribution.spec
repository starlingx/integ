%global with_devel 0
%global with_unit_test 0

%if 0%{?fedora} || 0%{?rhel} == 6
%global with_debug 1
%global with_check 1
%else
%global with_debug 0
%global with_check 0
%endif

%if 0%{?with_debug}
%global _dwz_low_mem_die_limit 0
%else
%global debug_package   %{nil}
%endif

%if ! 0%{?gobuild:1}
%define gobuild(o:) go build -ldflags "${LDFLAGS:-} -B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \\n')" -a -v -x %{?**};
%endif

%if ! 0%{?gotest:1}
%define gotest() go test -ldflags "${LDFLAGS:-}" %{?**}
%endif

%global provider        github
%global provider_tld    com
%global project         docker
%global repo            distribution
# https://github.com/docker/distribution
%global provider_prefix %{provider}.%{provider_tld}/%{project}/%{repo}
%global import_path     %{provider_prefix}
%global commit          48294d928ced5dd9b378f7fd7c6f5da3ff3f2c89
%global shortcommit     %(c=%{commit}; echo ${c:0:7})

Name:           %{project}-%{repo}
Version:        2.6.2
Release:        1%{?_tis_dist}.%{tis_patch_ver}
Summary:        Docker toolset to pack, ship, store, and deliver content
License:        ASL 2.0
URL:            https://%{provider_prefix}
Source0:        %{project}-%{repo}-%{version}.tar.gz
Source1:        %{name}.service
Source2:        config.yml
BuildRequires: systemd
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

Provides: docker-registry = %{version}-%{release}
Obsoletes: docker-registry <= 0.9.1-5

# e.g. el6 has ppc64 arch without gcc-go, so EA tag is required
ExclusiveArch:  %{?go_arches:%{go_arches}}%{!?go_arches:%{ix86} x86_64 %{arm}}
# If go_compiler is not set to 1, there is no virtual provide. Use golang instead.
BuildRequires:  %{?go_compiler:compiler(go-compiler)}%{!?go_compiler:golang}

%description
%{summary}

%if 0%{?with_devel}
%package devel
Summary:       %{summary}
BuildArch:     noarch

%if 0%{?with_check}
BuildRequires: golang(github.com/AdRoll/goamz/aws)
BuildRequires: golang(github.com/AdRoll/goamz/cloudfront)
BuildRequires: golang(github.com/AdRoll/goamz/s3)
BuildRequires: golang(github.com/Azure/azure-sdk-for-go/storage)
BuildRequires: golang(github.com/Sirupsen/logrus)
BuildRequires: golang(github.com/Sirupsen/logrus/formatters/logstash)
BuildRequires: golang(github.com/bugsnag/bugsnag-go)
BuildRequires: golang(github.com/denverdino/aliyungo/oss)
BuildRequires: golang(github.com/docker/libtrust)
BuildRequires: golang(github.com/garyburd/redigo/redis)
BuildRequires: golang(github.com/gorilla/handlers)
BuildRequires: golang(github.com/gorilla/mux)
BuildRequires: golang(github.com/mitchellh/mapstructure)
BuildRequires: golang(github.com/ncw/swift)
BuildRequires: golang(github.com/noahdesu/go-ceph/rados)
BuildRequires: golang(github.com/spf13/cobra)
BuildRequires: golang(github.com/stevvooe/resumable)
BuildRequires: golang(github.com/stevvooe/resumable/sha256)
BuildRequires: golang(github.com/stevvooe/resumable/sha512)
BuildRequires: golang(github.com/yvasiyarov/gorelic)
BuildRequires: golang(golang.org/x/crypto/bcrypt)
BuildRequires: golang(golang.org/x/net/context)
BuildRequires: golang(golang.org/x/oauth2)
BuildRequires: golang(golang.org/x/oauth2/google)
BuildRequires: golang(golang.org/x/oauth2/jwt)
BuildRequires: golang(google.golang.org/api/googleapi)
BuildRequires: golang(google.golang.org/api/storage/v1)
BuildRequires: golang(google.golang.org/cloud)
BuildRequires: golang(google.golang.org/cloud/storage)
BuildRequires: golang(gopkg.in/check.v1)
BuildRequires: golang(gopkg.in/yaml.v2)
%endif

Requires:      golang(github.com/AdRoll/goamz/aws)
Requires:      golang(github.com/AdRoll/goamz/cloudfront)
Requires:      golang(github.com/AdRoll/goamz/s3)
Requires:      golang(github.com/Azure/azure-sdk-for-go/storage)
Requires:      golang(github.com/Sirupsen/logrus)
Requires:      golang(github.com/Sirupsen/logrus/formatters/logstash)
Requires:      golang(github.com/bugsnag/bugsnag-go)
Requires:      golang(github.com/denverdino/aliyungo/oss)
Requires:      golang(github.com/docker/libtrust)
Requires:      golang(github.com/garyburd/redigo/redis)
Requires:      golang(github.com/gorilla/handlers)
Requires:      golang(github.com/gorilla/mux)
Requires:      golang(github.com/mitchellh/mapstructure)
Requires:      golang(github.com/ncw/swift)
Requires:      golang(github.com/noahdesu/go-ceph/rados)
Requires:      golang(github.com/spf13/cobra)
Requires:      golang(github.com/stevvooe/resumable)
Requires:      golang(github.com/stevvooe/resumable/sha256)
Requires:      golang(github.com/stevvooe/resumable/sha512)
Requires:      golang(github.com/yvasiyarov/gorelic)
Requires:      golang(golang.org/x/crypto/bcrypt)
Requires:      golang(golang.org/x/net/context)
Requires:      golang(golang.org/x/oauth2)
Requires:      golang(golang.org/x/oauth2/google)
Requires:      golang(golang.org/x/oauth2/jwt)
Requires:      golang(google.golang.org/api/googleapi)
Requires:      golang(google.golang.org/api/storage/v1)
Requires:      golang(google.golang.org/cloud)
Requires:      golang(google.golang.org/cloud/storage)
Requires:      golang(gopkg.in/check.v1)
Requires:      golang(gopkg.in/yaml.v2)

Provides:      golang(%{import_path}) = %{version}-%{release}
Provides:      golang(%{import_path}/configuration) = %{version}-%{release}
Provides:      golang(%{import_path}/context) = %{version}-%{release}
Provides:      golang(%{import_path}/digest) = %{version}-%{release}
Provides:      golang(%{import_path}/health) = %{version}-%{release}
Provides:      golang(%{import_path}/health/api) = %{version}-%{release}
Provides:      golang(%{import_path}/health/checks) = %{version}-%{release}
Provides:      golang(%{import_path}/manifest) = %{version}-%{release}
Provides:      golang(%{import_path}/manifest/manifestlist) = %{version}-%{release}
Provides:      golang(%{import_path}/manifest/schema1) = %{version}-%{release}
Provides:      golang(%{import_path}/manifest/schema2) = %{version}-%{release}
Provides:      golang(%{import_path}/notifications) = %{version}-%{release}
Provides:      golang(%{import_path}/reference) = %{version}-%{release}
Provides:      golang(%{import_path}/registry) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/api/errcode) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/api/v2) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/auth) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/auth/htpasswd) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/auth/silly) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/auth/token) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/client) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/client/auth) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/client/transport) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/handlers) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/listener) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/middleware/registry) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/middleware/repository) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/proxy) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/proxy/scheduler) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/cache) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/cache/cachecheck) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/cache/memory) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/cache/redis) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/driver) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/driver/azure) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/driver/base) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/driver/factory) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/driver/filesystem) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/driver/gcs) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/driver/inmemory) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/driver/middleware) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/driver/middleware/cloudfront) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/driver/oss) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/driver/rados) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/driver/s3) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/driver/swift) = %{version}-%{release}
Provides:      golang(%{import_path}/registry/storage/driver/testsuites) = %{version}-%{release}
Provides:      golang(%{import_path}/testutil) = %{version}-%{release}
Provides:      golang(%{import_path}/uuid) = %{version}-%{release}
Provides:      golang(%{import_path}/version) = %{version}-%{release}

%description devel
%{summary}

This package contains library source intended for
building other packages which use import path with
%{import_path} prefix.
%endif

%if 0%{?with_unit_test} && 0%{?with_devel}
%package unit-test
Summary:         Unit tests for %{name} package
# If go_compiler is not set to 1, there is no virtual provide. Use golang instead.
BuildRequires:  %{?go_compiler:compiler(go-compiler)}%{!?go_compiler:golang}

%if 0%{?with_check}
#Here comes all BuildRequires: PACKAGE the unit tests
#in %%check section need for running
%endif

# test subpackage tests code from devel subpackage
Requires:        %{name}-devel = %{version}-%{release}

%if 0%{?with_check}
BuildRequires: golang(github.com/ncw/swift/swifttest)
%endif

%description unit-test
%{summary}

This package contains unit tests for project
providing packages with %{import_path} prefix.
%endif

%prep
%setup -q -n %{project}-%{repo}-%{version}
sed -i 's/elliptic.P224(), //' vendor/golang.org/x/crypto/ocsp/ocsp.go


%build
mkdir -p src/github.com/%{project}
ln -s ../../../ src/%{import_path}
export GOPATH=$(pwd):$(pwd)/Godeps/_workspace:%{gopath}
%gobuild -o bin/registry %{import_path}/cmd/registry

%install
install -d -p %{buildroot}%{_bindir}
install -p -m 0755 bin/registry %{buildroot}%{_bindir}

# install systemd/init scripts
install -d %{buildroot}%{_unitdir}
install -p -m 644 %{SOURCE1} %{buildroot}%{_unitdir}

# install config file
install -d -p %{buildroot}%{_sysconfdir}/%{name}/registry
install -p -m 644 %{SOURCE2} %{buildroot}%{_sysconfdir}/%{name}/registry

# install root dir
install -d %{buildroot}%{_sharedstatedir}/registry

# source code for building projects
%if 0%{?with_devel}
install -d -p %{buildroot}/%{gopath}/src/%{import_path}/
echo "%%dir %%{gopath}/src/%%{import_path}/." >> devel.file-list
# find all *.go but no *_test.go files and generate devel.file-list
for file in $(find . -iname "*.go" \! -iname "*_test.go") ; do
    echo "%dir %{gopath}/src/%{import_path}/$(dirname $file)" >> devel.file-list
    install -d -p %{buildroot}/%{gopath}/src/%{import_path}/$(dirname $file)
    cp -pav $file %{buildroot}/%{gopath}/src/%{import_path}/$file
    echo "%{gopath}/src/%{import_path}/$file" >> devel.file-list
done
%endif

# testing files for this project
%if 0%{?with_unit_test} && 0%{?with_devel}
install -d -p %{buildroot}/%{gopath}/src/%{import_path}/
# find all *_test.go files and generate unit-test.file-list
for file in $(find . -iname "*_test.go"); do
    echo "%dir %{gopath}/src/%{import_path}/$(dirname $file)" >> devel.file-list
    install -d -p %{buildroot}/%{gopath}/src/%{import_path}/$(dirname $file)
    cp -pav $file %{buildroot}/%{gopath}/src/%{import_path}/$file
    echo "%{gopath}/src/%{import_path}/$file" >> unit-test.file-list
done
%endif

%if 0%{?with_devel}
sort -u -o devel.file-list devel.file-list
%endif

%check
%if 0%{?with_check} && 0%{?with_unit_test} && 0%{?with_devel}
export GOPATH=%{buildroot}/%{gopath}:$(pwd)/Godeps/_workspace:%{gopath}
make test
%endif

%pre

%post
%systemd_post %{name}.service

%preun
%systemd_preun %{name}.service

%postun
%systemd_postun_with_restart %{name}.service

#define license tag if not already defined
%{!?_licensedir:%global license %doc}

%files
%if 0%{?fedora} >= 23
%license LICENSE
%else
%doc LICENSE
%endif
%doc AUTHORS CONTRIBUTING.md MAINTAINERS README.md
%{_bindir}/registry
%{_unitdir}/%{name}.service
%dir %{_sharedstatedir}/registry
%config(noreplace) %{_sysconfdir}/%{name}/registry/config.yml

%if 0%{?with_devel}
%files devel -f devel.file-list
%if 0%{?fedora} >= 23
%license LICENSE
%else
%doc LICENSE
%endif
%doc CONTRIBUTING.md README.md ROADMAP.md AUTHORS
%dir %{gopath}/src/%{provider}.%{provider_tld}/%{project}
%endif

%if 0%{?with_unit_test} && 0%{?with_devel}
%files unit-test -f unit-test.file-list
%license LICENSE
%doc CONTRIBUTING.md README.md ROADMAP.md AUTHORS
%endif

%changelog
* Tue Jul 25 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2.6.2-1.git48294d9
- Resolves: #1474894 - CVE-2017-11468
- bump to tag 2.6.2
- built commit 48294d9
- built with bundled dependencies

* Fri Feb 10 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2.5.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Fri Sep 23 2016 Frantisek Kluknavsky <fkluknav@redhat.com> - 2.5.1-1
- Resolves: #1346484 - rebase to v2.5.1

* Thu Jul 21 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.4.1-2
- https://fedoraproject.org/wiki/Changes/golang1.7

* Mon May 23 2016 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2.4.1-1
- Resolves: #1311327 - rebase to v2.4.1

* Fri Mar 04 2016 jchaloup <jchaloup@redhat.com> - 2.3.0-3
- Provide devel subpackage
- Build from debundled dependencies

* Mon Feb 22 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.3.0-2
- https://fedoraproject.org/wiki/Changes/golang1.6

* Mon Feb 15 2016 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2.3.0-1
- Resolves: rhbz#1277743 - bump to v2.3.0
- Resolves: rhbz#1308656 - obsolete docker-registry <= 0.9.1-5

* Wed Feb 03 2016 Fedora Release Engineering <releng@fedoraproject.org> - 2.3.0-0.2.rc1
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Thu Jan 28 2016 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2.3.0-0.1.rc1
- Resolves: rhbz#1277743 - bump to v2.3.0-rc1

* Wed Oct 28 2015 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2.1.1-4
- Resolves: rhbz#1276046 - correct yml file location in unitfile

* Wed Oct 07 2015 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2.1.1-3
- do not install sysconfig file
- Install root dir /var/lib/registry

* Tue Sep 22 2015 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2.1.1-2
- systemd is a dep

* Thu Sep 17 2015 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2.1.1-1
- First package for Fedora
  resolves: #1259005
