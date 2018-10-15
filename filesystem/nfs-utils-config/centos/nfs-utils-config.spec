Summary: nfs-utils-config
Name: nfs-utils-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Requires: nfs-utils
Summary: package customized configuration and service files of nfs-utils to system folder.

%description
package customized configuration and service files of nfs-utils to system folder.

%prep
%setup

%build

%install
install -d %{buildroot}%{_sysconfdir}/init.d
install -d %{buildroot}%{_unitdir}
install -d %{buildroot}%{_datadir}/starlingx
install -m 755 -p -D nfscommon %{buildroot}%{_sysconfdir}/init.d
install -m 644 -p -D nfscommon.service %{buildroot}%{_unitdir}
install -m 755 -p -D nfsserver %{buildroot}%{_sysconfdir}/init.d
install -m 644 -p -D nfsserver.service %{buildroot}%{_unitdir}
install -m 644 -p -D nfsmount.conf %{buildroot}%{_datadir}/starlingx/stx.nfsmount.conf

%post
if [ $1 -eq 1 ] ; then
        # Initial installation
        cp -f %{_datadir}/starlingx/stx.nfsmount.conf %{_sysconfdir}/nfsmount.conf
        chmod 644 %{_sysconfdir}/nfsmount.conf
fi
/bin/systemctl enable nfscommon.service  >/dev/null 2>&1 || :
/bin/systemctl enable nfsserver.service  >/dev/null 2>&1 || :

%files
%defattr(-,root,root,-)
%{_sysconfdir}/init.d/nfscommon
%{_unitdir}/nfscommon.service
%{_sysconfdir}/init.d/nfsserver
%{_unitdir}/nfsserver.service
%{_datadir}/starlingx/stx.nfsmount.conf
