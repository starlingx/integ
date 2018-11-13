Summary: pam-config
Name: pam-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Requires: pam
Summary: package StarlingX configuration files of pam to system folder.

%description
package StarlingX configuration files of pam to system folder.

%prep
%setup

%build

%install
%define _pamconfdir %{_sysconfdir}/pam.d
%{__install}  -d  %{buildroot}%{_pamconfdir}
%{__install}  -m 644 common-account  %{buildroot}%{_pamconfdir}/common-account
%{__install}  -m 644 common-auth     %{buildroot}%{_pamconfdir}/common-auth
%{__install}  -m 644 common-password %{buildroot}%{_pamconfdir}/common-password
%{__install}  -m 644 common-session  %{buildroot}%{_pamconfdir}/common-session
%{__install}  -m 644 common-session-noninteractive %{buildroot}%{_pamconfdir}/common-session-noninteractive

%post

%files
%config(noreplace) %{_pamconfdir}/common-account
%config(noreplace) %{_pamconfdir}/common-auth
%config(noreplace) %{_pamconfdir}/common-password
%config(noreplace) %{_pamconfdir}/common-session
%config(noreplace) %{_pamconfdir}/common-session-noninteractive
