Summary: rsync-config
Name: rsync-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Requires: rsync
Summary: package StarlingX configuration files of rsync to system folder.

%description
package StarlingX configuration files of rsync to system folder.

%prep
%setup

%build

%install
%{__install} -d  %{buildroot}%{_datadir}/starlingx/
%{__install} -m 644 rsyncd.conf  %{buildroot}%{_datadir}/starlingx/stx.rsyncd.conf

%post
if [ $1 -eq 1 ] ; then
        # Initial installation
        cp -f %{_datadir}/starlingx/stx.rsyncd.conf  %{_sysconfdir}/rsyncd.conf
fi

%files
%{_datadir}/starlingx/stx.rsyncd.conf
