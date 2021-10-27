%global githubname   libbpf
%global githubver    0.5.0
%global githubfull   %{githubname}-%{githubver}

Name:           %{githubname}
Version:        %{githubver}
Release:        1%{?_tis_dist}.%{tis_patch_ver}
Summary:        Libbpf library

License:        LGPLv2 or BSD
URL:            https://github.com/%{githubname}/%{githubname}
Source:         %{githubname}-%{githubver}.tar.gz
BuildRequires:  gcc elfutils-libelf-devel elfutils-devel
BuildRequires: make
%if 0%{?rhel} == 7
BuildRequires:  devtoolset-8-build
BuildRequires:  devtoolset-8-binutils
BuildRequires:  devtoolset-8-gcc
BuildRequires:  devtoolset-8-make
%endif

# This package supersedes libbpf from kernel-tools,
# which has default Epoch: 0. By having Epoch: > 0
# this libbpf will take over smoothly
Epoch:          2

%description
A mirror of bpf-next linux tree bpf-next/tools/lib/bpf directory plus its
supporting header files. The version of the package reflects the version of
ABI.

%package devel
Summary:        Development files for %{name}
Requires:       %{name} = 2:%{version}-%{release}
Requires:       kernel-headers >= 5.10.0
Requires:       zlib

%description devel
The %{name}-devel package contains libraries header files for
developing applications that use %{name}

%package static
Summary: Static library for libbpf development
Requires: %{name}-devel = 2:%{version}-%{release}

%description static
The %{name}-static package contains static library for
developing applications that use %{name}

%define _lto_cflags %{nil}

%global make_flags DESTDIR=%{buildroot} OBJDIR=%{_builddir} CFLAGS="%{build_cflags} -fPIC" LDFLAGS="%{build_ldflags} -Wl,--no-as-needed" LIBDIR=/%{_libdir} NO_PKG_CONFIG=1

%prep
%if 0%{?rhel} == 7
source scl_source enable devtoolset-8 || :
%endif

%autosetup -n %{githubfull}

%build
%if 0%{?rhel} == 7
source scl_source enable devtoolset-8 || :
%endif

%make_build -C ./src %{make_flags}

%install
%if 0%{?rhel} == 7
source scl_source enable devtoolset-8 || :
%endif

%make_install -C ./src %{make_flags}

%files
%{_libdir}/libbpf.so.%{version}
%{_libdir}/libbpf.so.0

%files devel
%{_libdir}/libbpf.so
%{_includedir}/bpf/
%{_libdir}/pkgconfig/libbpf.pc

%files static
%{_libdir}/libbpf.a

%changelog
* Wed Oct 27 2021 M. Vefa Bicakci <vefa.bicakci@windriver.com> - 2:0.5.0-1.tis
- Adapt to StarlingX. The base spec file was acquired from:
  https://src.fedoraproject.org/rpms/libbpf/blob/main/f/libbpf.spec
- Change the kernel-headers requirement from 5.14.0 to 5.10.0. This should
  not be an issue, as libbpf advertises itself to be kernel-version agnostic.
- Add build-time dependency on devtoolset-8 and make the build use it.
- Trim all changelog entries belonging to years before 2021.

* Fri Sep 10 2021 Jiri Olsa <jolsa@redhat.com> - 2:0.5.0-1
- release 0.5.0-1

* Thu Jul 22 2021 Fedora Release Engineering <releng@fedoraproject.org> - 2:0.4.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_35_Mass_Rebuild

* Wed May 26 2021 Jiri Olsa <jolsa@redhat.com> - 2:0.4.0-1
- release 0.4.0-1

* Tue Jan 26 2021 Fedora Release Engineering <releng@fedoraproject.org> - 2:0.3.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_34_Mass_Rebuild

* Fri Jan 22 2021 Jiri Olsa <jolsa@redhat.com> - 2:0.3.0-1
- release 0.3.0-1
