%global with_debug 1

%if 0%{?with_debug}
%global _dwz_low_mem_die_limit 0
%else
%global debug_package   %{nil}
%endif

%if ! 0%{?gobuild:1}
%define gobuild(o:) go build -buildmode pie -tags=rpm_crashtraceback -ldflags "${LDFLAGS:-} -B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \\n') -extldflags '-Wl,-z,relro,-z,now'" -a -v -x %{?**};
%endif

%global provider        github
%global provider_tld    com
%global project         coreos
%global repo            etcd
# https://github.com/coreos/etcd
%global provider_prefix %{provider}.%{provider_tld}/%{project}/%{repo}
%global import_path     %{provider_prefix}
%global commit          1674e682fe9fbecd66e9f20b77da852ad7f517a9
%global shortcommit     %(c=%{commit}; echo ${c:0:7})

%global system_name     etcd

Name:		etcd
Version:	3.3.15
Release:        1%{?_tis_dist}.%{tis_patch_ver}
Summary:	A highly-available key value store for shared configuration
License:	ASL 2.0
URL:		https://%{provider_prefix}
Source0:        %{name}-v%{version}.tar.gz
Source1:	%{system_name}.service
Source2:	%{system_name}.conf

# e.g. el6 has ppc64 arch without gcc-go, so EA tag is required
ExclusiveArch:  %{?go_arches:%{go_arches}}%{!?go_arches:x86_64 aarch64 ppc64le s390x}

# If go_compiler is not set to 1, there is no virtual provide. Use golang instead.
# Build with our own prefered golang, not 1.11 from CentOS
# BuildRequires:  %{?go_compiler:compiler(go-compiler)}%{!?go_compiler:golang}
BuildRequires:  %{?go_compiler:compiler(go-compiler)}%{!?go_compiler:golang >= 1.13}

Obsoletes: etcd3 < 3.0.15
Provides: etcd3 = %{version}-%{release}

BuildRequires: libpcap-devel

BuildRequires:	systemd

Requires(pre):	shadow-utils
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

%description
A highly-available key value store for shared configuration.

%prep
%setup -q -n %{repo}-v%{version}

# move content of vendor under Godeps as has been so far
mkdir -p Godeps/_workspace/src
mv vendor/* Godeps/_workspace/src/.

%build
mkdir -p src/github.com/coreos
ln -s ../../../ src/github.com/coreos/etcd

export GOPATH=$(pwd):$(pwd)/Godeps/_workspace:%{gopath}
go env -w GO111MODULE=auto

export LDFLAGS="-X %{import_path}/version.GitSHA=%{shortcommit} -B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \n')"

%gobuild -o bin/%{system_name} %{import_path}
%gobuild -o bin/%{system_name}ctl %{import_path}/%{system_name}ctl

%install
install -D -p -m 0755 bin/%{system_name} %{buildroot}%{_bindir}/%{system_name}
install -D -p -m 0755 bin/%{system_name}ctl %{buildroot}%{_bindir}/%{system_name}ctl
install -D -p -m 0644 %{SOURCE1} %{buildroot}%{_unitdir}/%{system_name}.service
install -d -m 0755 %{buildroot}%{_sysconfdir}/%{system_name}
install -m 644 -t %{buildroot}%{_sysconfdir}/%{system_name} %{SOURCE2}

# And create /var/lib/etcd
install -d -m 0755 %{buildroot}%{_sharedstatedir}/%{system_name}

%pre
getent group %{system_name} >/dev/null || groupadd -r %{system_name}
getent passwd %{system_name} >/dev/null || useradd -r -g %{system_name} -d %{_sharedstatedir}/%{system_name} \
	-s /sbin/nologin -c "etcd user" %{system_name}

%post
%systemd_post %{system_name}.service

%preun
%systemd_preun %{system_name}.service

%postun
%systemd_postun %{system_name}.service

#define license tag if not already defined
%{!?_licensedir:%global license %doc}

%files
%license LICENSE
%doc *.md
%doc glide.lock
%config(noreplace) %{_sysconfdir}/%{system_name}
%{_bindir}/%{system_name}
%{_bindir}/%{system_name}ctl
%dir %attr(-,%{system_name},%{system_name}) %{_sharedstatedir}/%{system_name}
%{_unitdir}/%{system_name}.service

%changelog
* Mon Jun 11 2018 Jan Chaloupka <jchaloup@redhat.com> - 3.2.22-1
- Update to 3.2.22
  resolves: #1541355

* Mon Jun 04 2018 Jan Chaloupka <jchaloup@redhat.com> - 3.2.21-1
- Update to 3.2.21
  resolves: #1585787

* Tue Apr 17 2018 Jan Chaloupka <jchaloup@redhat.com> - 3.2.18-1
- Update to 3.2.18
  resolves: #1568389

* Tue Feb 06 2018 Jan Chaloupka <jchaloup@redhat.com> - 3.2.15-2
- Rebuild for 7.5.0
  resolves: #1542526

* Mon Jan 29 2018 Jan Chaloupka <jchaloup@redhat.com> - 3.2.15-1
- Update to 3.2.15
  resolves: #1539670
  resolves: #1378706

* Wed Dec 06 2017 Jan Chaloupka <jchaloup@redhat.com> - 3.2.11-1
- Update to 3.2.11
  related: #1514612

* Tue Nov 21 2017 Jan Chaloupka <jchaloup@redhat.com> - 3.2.10-1
- Update to 3.2.10
  resolves: #1514612

* Mon Nov 20 2017 Jan Chaloupka <jchaloup@redhat.com> - 3.2.9-3
- Bump man-pages tarball
  related: #1510480

* Mon Nov 20 2017 Jan Chaloupka <jchaloup@redhat.com> - 3.2.9-2
- Fix Synopsis of etcdctl3 man pages
  related: #1510480

* Tue Nov 07 2017 Jan Chaloupka <jchaloup@redhat.com> - 3.2.9-1
- Update to 3.2.9
  resolves: #1510480
- Generate etcd and etcdctl man-pages
  resolves: #1444336

* Fri Sep 29 2017 Jan Chaloupka <jchaloup@redhat.com> - 3.2.7-2
- Rebuild with correct hardening flags
  resolves: #1420783

* Tue Sep 19 2017 Jan Chaloupka <jchaloup@redhat.com> - 3.2.7-1
- Update to 3.2.7
  resolves: #1493165

* Tue Aug 08 2017 Jan Chaloupka <jchaloup@redhat.com> - 3.2.5-1
- Update to 3.2.5
  resolves: #1479371

* Mon Jun 12 2017 Jan Chaloupka <jchaloup@redhat.com> - 3.1.9-2
- Build for secondary architectures as well

* Fri Jun 09 2017 Scott Dodson <sdodson@redhat.com> - 3.1.9-1
- Update to 3.1.9
  resolves: #1458941

* Tue Jun 06 2017 Jan Chaloupka <jchaloup@redhat.com> - 3.1.8-1
- Update to 3.1.8
  resolves: #1459122

* Tue May 02 2017 Jan Chaloupka <jchaloup@redhat.com> - 3.1.7-1
- Update to 3.1.7
  resolves: #1447235

* Tue Apr 04 2017 Yaakov Selkowitz <yselkowi@redhat.com> - 3.1.3-2
- Circumvent runtime check of officially supported architectures
  resolves: #1434973

* Tue Mar 21 2017 Jan Chaloupka <jchaloup@redhat.com> - 3.1.3-1
- Update to 3.1.3
  resolves: #1434364

* Mon Feb 27 2017 Josh Boyer <jwboyer@redhat.com> - 3.1.0-2.1
- Rebuild rebase on all architectures

* Tue Feb 21 2017 Jan Chaloupka <jchaloup@redhat.com> - 3.1.0-2
- Apply "add --keep-cluster-id and --node-id to 'etcdctl backup'"
  from extras-rhel-7.2 branch
  resolves: #1350875

* Thu Feb 16 2017 Josh Boyer <jwboyer@redhat.com> - 3.1.0-1.1
- Rebuild rebase on all architectures

* Mon Feb 06 2017 Jan Chaloupka <jchaloup@redhat.com> - 3.1.0-1
- Update to 3.1.0
  etcdctl-top removed by upstream
  resolves: #1416440

* Fri Jan 20 2017 d.marlin <dmarlin@redhat.com>
- Build for all archs (adding ppc64le and s390x)

* Tue Jan 10 2017 d.marlin <dmarlin@redhat.com> 
- Add aarch64 to ExclusiveArch list.

* Mon Jan 09 2017 d.marlin <dmarlin@redhat.com> 
- Correct 'link' warning for -X flag.

* Thu Dec 01 2016 jchaloup <jchaloup@redhat.com> - 3.0.15-1
- Update to 3.0.15
  Obsolete etcd3 < 3.0.15

* Fri Nov 18 2016 jchaloup <jchaloup@redhat.com> - 3.0.14-3
- Build with debug-info subpackage
- Until etcd3 obsoletes etcd it conflicts with it

* Tue Nov 15 2016 Avesh Agarwal <avagarwa@redhat.com> - 3.0.14-2
- Resolves: #1395359 etcd3 should not obsolete etcd

* Mon Nov 07 2016 jchaloup <jchaloup@redhat.com> - 3.0.14-1
- Update to v3.0.14
  related: #1386963

* Thu Oct 27 2016 jchaloup <jchaloup@redhat.com> - 3.0.13-1
- Update to v3.0.13
  related: #1386963

* Fri Oct 21 2016 jchaloup <jchaloup@redhat.com> - 3.0.12-3
- etcdctl: fix migrate in outputing client.Node to json
  resolves: #1386963

* Tue Oct 18 2016 jchaloup <jchaloup@redhat.com> - 3.0.12-2
- Replace etcd with etcd3 when upgrading
  resolves: #1384161

* Thu Oct 13 2016 jchaloup <jchaloup@redhat.com> - 3.0.12-1
- Update to v3.0.12

* Thu Oct 06 2016 jchaloup <jchaloup@redhat.com> - 3.0.10-1
- Update to v3.0.10

* Fri Sep 23 2016 jchaloup <jchaloup@redhat.com> - 3.0.3-2
- Extend etcd.conf with new flags
  resolves: #1378706

* Fri Jul 22 2016 jchaloup <jchaloup@redhat.com> - 3.0.2-1
- Update to v3.0.3
  related: #1347499

* Tue Jul 12 2016 jchaloup <jchaloup@redhat.com> - 3.0.2-1
- Update to v3.0.2
  related: #1347499

* Sun May 15 2016 jchaloup <jchaloup@redhat.com> - 3.0.0-0.1.beta0
- Build etcd3 v3.0.0-beta0 for AH 7.3
  resolves: #1347499
