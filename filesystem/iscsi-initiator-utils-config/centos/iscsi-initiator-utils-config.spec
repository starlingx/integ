Summary: iscsi-initiator-utils-config
Name: iscsi-initiator-utils-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Requires: iscsi-initiator-utils
Summary: package StarlingX configuration files of iscsi-initiator-utils to system folder.

%description
package StarlingX configuration files of iscsi-initiator-utils to system folder.

%prep
%setup

%build

%install
%{__install} -d  %{buildroot}%{_tmpfilesdir}
%{__install} -d  %{buildroot}%{_sysconfdir}/systemd/system
%{__install} -d  %{buildroot}%{_datadir}/starlingx

%{__install} -m 0644 iscsi-cache.volatiles   %{buildroot}%{_tmpfilesdir}/iscsi-cache.conf
%{__install} -m 0644 iscsi-shutdown.service  %{buildroot}%{_sysconfdir}/systemd/system
%{__install} -m 0644 iscsid.conf             %{buildroot}%{_datadir}/starlingx/stx.iscsid.conf

%post
if [ $1 -eq 1 ] ; then
        # Initial installation
        cp -f %{_datadir}/starlingx/stx.iscsid.conf %{_sysconfdir}/iscsi/iscsid.conf
fi
/bin/systemctl disable iscsi-shutdown.service

%files
%{_tmpfilesdir}/iscsi-cache.conf
%{_sysconfdir}/systemd/system/iscsi-shutdown.service
%{_datadir}/starlingx/stx.iscsid.conf
