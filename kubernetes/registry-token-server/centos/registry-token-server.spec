%if ! 0%{?gobuild:1}
%define gobuild(o:) go build -ldflags "${LDFLAGS:-} -B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \\n')" -a -v -x %{?**};
%endif

Name:           registry-token-server
Version:        1.0.0
Release:        1%{?_tis_dist}.%{tis_patch_ver}
Summary:        Token server for use with Docker registry with Openstack Keystone back end
License:        ASL 2.0
Source0:        registry-token-server-%{version}.tar.gz
Source1:        %{name}.service
Source2:        token_server.conf

BuildRequires: systemd
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

BuildRequires:  golang >= 1.6
BuildRequires:  golang-dep
ExclusiveArch:  %{?go_arches:%{go_arches}}%{!?go_arches:%{ix86} x86_64 %{arm}}

%description
%{summary}

%prep
%setup -q -n registry-token-server-%{version}

%build
mkdir -p ./_build/src/
ln -s $(pwd) ./_build/src/registry-token-server
export GOPATH=$(pwd)/_build:%{gopath}

cd ./_build/src/registry-token-server
dep ensure
%gobuild -o bin/registry-token-server registry-token-server

%install
install -d -p %{buildroot}%{_bindir}
install -p -m 0755 bin/registry-token-server %{buildroot}%{_bindir}

# install systemd/init scripts
install -d %{buildroot}%{_unitdir}
install -p -m 644 %{SOURCE1} %{buildroot}%{_unitdir}

# install directory to install default certificate
install -d -p %{buildroot}%{_sysconfdir}/ssl/private

# install environment variables file for service file
install -d -p %{buildroot}%{_sysconfdir}/%{name}/registry
install -p -m 644 %{SOURCE2} %{buildroot}%{_sysconfdir}/%{name}/registry

#define license tag if not already defined
%{!?_licensedir:%global license %doc}

%files
%doc LICENSE

%{_bindir}/registry-token-server
%{_unitdir}/%{name}.service
%{_sysconfdir}/%{name}/registry/token_server.conf
