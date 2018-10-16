Summary: StarlingX Sudo Configuration File
Name: sudo-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown

Source0: wrs.sudo
Source1: LICENSE

%define WRSROOT_P cBglipPpsKwBQ

%description
StarlingX sudo configuration file

%install
install -d %{buildroot}/%{_sysconfdir}/sudoers.d
install -m 440 %{SOURCE0}  %{buildroot}/%{_sysconfdir}/sudoers.d/wrs

%pre
getent group wrs >/dev/null || groupadd -r wrs
getent group wrs_protected >/dev/null || groupadd -f -g 345 wrs_protected
getent passwd wrsroot > /dev/null || \
useradd -m -g wrs -G root,wrs_protected \
    -d /home/wrsroot -p %{WRSROOT_P} \
    -s /bin/sh wrsroot 2> /dev/null || :

%files
%license ../SOURCES/LICENSE
%config(noreplace) %{_sysconfdir}/sudoers.d/wrs
