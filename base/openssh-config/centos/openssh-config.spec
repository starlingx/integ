Summary: openssh-config
Name: openssh-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Requires: %{_bindir}/systemctl
Requires: openssh
Summary: package StarlingX configuration files of openssh to system folder.

%description
package StarlingX configuration files of openssh to system folder.

%prep
%setup

%build

%install
%{__install} -d  %{buildroot}%{_datadir}/starlingx
%{__install} -d  %{buildroot}%{_sysconfdir}/systemd/system
%{__install} -m 644 sshd.pam      %{buildroot}%{_datadir}/starlingx/sshd.pam
%{__install} -m 644 sshd.service  %{buildroot}%{_sysconfdir}/systemd/system/sshd.service
%{__install} -m 644 ssh_config    %{buildroot}%{_datadir}/starlingx/ssh_config
%{__install} -m 600 sshd_config   %{buildroot}%{_datadir}/starlingx/sshd_config

%post
%define _pamconfdir %{_sysconfdir}/pam.d
if [ $1 -eq 1 ] ; then
        # Initial installation
        cp -f %{_datadir}/starlingx/sshd.pam    %{_pamconfdir}/sshd
        cp -f %{_datadir}/starlingx/ssh_config  %{_sysconfdir}/ssh/ssh_config
        cp -f %{_datadir}/starlingx/sshd_config %{_sysconfdir}/ssh/sshd_config
fi

%files
%{_datadir}/starlingx/sshd.pam
%{_sysconfdir}/systemd/system/sshd.service
%{_datadir}/starlingx/ssh_config
%{_datadir}/starlingx/sshd_config
