Name: nfscheck
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
Summary: NFS Audit

Group: base
License: Apache-2.0
URL: unknown
Source0: nfscheck.sh
Source1: nfscheck.service
Source2: LICENSE

Requires: systemd
Requires: util-linux

%description
NFS Audit


%prep


%build


%install
install -d -m 755 %{buildroot}/usr/bin/
install -m 755 %{SOURCE0} %{buildroot}/usr/bin/nfscheck.sh

install -d -m 755 %{buildroot}/usr/lib/systemd/system/
install -m 664 %{SOURCE1} %{buildroot}/usr/lib/systemd/system/nfscheck.service

%post
/usr/bin/systemctl enable nfscheck.service >/dev/null 2>&1

%files
%license ../SOURCES/LICENSE
/usr/bin/*
/usr/lib/systemd/system/*


%changelog

