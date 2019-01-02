Name:           golang-dep
Version:        0.5.0
Release:        %{tis_patch_ver}%{?_tis_dist}
Summary:        Go dep dependency management tool
Group:          Development/Languages
License:        Go
URL:            https://github.com/golang/dep
Source:         dep-v0.5.0.tar.gz
BuildRequires:  golang
Requires:       golang

%global with_debug 0
%global debug_package %{nil}
%define __spec_install_post %{nil}

%define tooldir %{_libdir}/go/pkg/%{name}/linux_amd64

%if ! 0%{?gobuild:1}
%define gobuild(o:) go build -ldflags "${LDFLAGS:-} -B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \\n')" -a -v -x %{?**};
%endif

%description
This package includes additional go development tools.

%prep
%setup -T -c -n go/src/github.com/golang/dep
tar --strip-components=1 -x -f %{SOURCE0}

%build
export GOPATH=%{_builddir}/go
(cd cmd/dep && %gobuild -o dep)

%install
rm -rf %{buildroot}
install -d %{buildroot}%{_bindir}
install -d %{buildroot}%{tooldir}
install cmd/dep/dep %{buildroot}%{_bindir}

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{_bindir}/dep

