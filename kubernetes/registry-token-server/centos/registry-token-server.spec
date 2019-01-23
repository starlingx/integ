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

# Go dependencies downloaded as tarballs
Source10:       Sirupsen-logrus-55eb11d21d2a31a3cc93838241d04800f52e823d.tar.gz
Source11:       docker-distribution-48294d928ced5dd9b378f7fd7c6f5da3ff3f2c89.tar.gz
Source12:       docker-libtrust-fa567046d9b14f6aa788882a950d69651d230b21.tar.gz
Source13:       gophercloud-gophercloud-aa00757ee3ab58e53520b6cb910ca0543116400a.tar.gz
Source14:       gorilla-context-08b5f424b9271eedf6f9f0ce86cb9396ed337a42.tar.gz
Source15:       gorilla-mux-456bcfa82d672db7cae587c9b541463f65bc2718.tar.gz

BuildRequires: systemd
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

BuildRequires:  golang >= 1.6
ExclusiveArch:  %{?go_arches:%{go_arches}}%{!?go_arches:%{ix86} x86_64 %{arm}}

%description
%{summary}

%prep
%setup -q -n registry-token-server-%{version}

# Extract other go dependencies
%setup -T -D -a 10
%setup -T -D -a 11
%setup -T -D -a 12
%setup -T -D -a 13
%setup -T -D -a 14
%setup -T -D -a 15
mkdir -p _build/src/github.com/gorilla/ && mv gorilla-mux _build/src/github.com/gorilla/mux
mkdir -p _build/src/github.com/docker/ && mv docker-distribution _build/src/github.com/docker/distribution
mkdir -p _build/src/github.com/docker/ && mv docker-libtrust _build/src/github.com/docker/libtrust
mkdir -p _build/src/github.com/docker/distribution/ && mv gorilla-context _build/src/github.com/docker/distribution/context
mkdir -p _build/src/github.com/Sirupsen/ && mv Sirupsen-logrus _build/src/github.com/Sirupsen/logrus
mkdir -p _build/src/github.com/gophercloud && mv gophercloud-gophercloud _build/src/github.com/gophercloud/gophercloud

%build
mkdir -p ./_build/src/
ln -s $(pwd) ./_build/src/registry-token-server
export GOPATH=$(pwd)/_build:%{gopath}

cd ./_build/src/registry-token-server
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
