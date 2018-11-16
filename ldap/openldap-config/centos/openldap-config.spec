Summary: StarlingX openldap Configuration File
Name: openldap-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: config-files
Packager: StarlingX
URL: unknown
Source: %name-%version.tar.gz

BuildArch: noarch
Requires: openldap-servers

%define debug_package %{nil}

%description
StarlingX openldap configuration file

%prep

%setup

%build

%install
mkdir -p %{buildroot}%{_sysconfdir}/rc.d/init.d
install -m 755 initscript %{buildroot}%{_sysconfdir}/rc.d/init.d/openldap
install -d -m 740 %{buildroot}%{_sysconfdir}/openldap
install -m 600 slapd.conf %{buildroot}%{_sysconfdir}/openldap/slapd.conf
install -m 600 initial_config.ldif %{buildroot}%{_sysconfdir}/openldap/initial_config.ldif

install -d %{buildroot}%{_datadir}/starlingx
install -m 644 slapd.service %{buildroot}%{_datadir}/starlingx/slapd.service
install -m 644 slapd.sysconfig %{buildroot}%{_datadir}/starlingx/slapd.sysconfig


%post
if [ $1 -eq 1 ] ; then
    cp -f %{_datadir}/starlingx/slapd.service %{_unitdir}/slapd.service
    chmod 644 %{_unitdir}/slapd.service
    cp -f %{_datadir}/starlingx/slapd.sysconfig %{_sysconfdir}/sysconfig/slapd
    chmod 644 %{_unitdir}/slapd
fi

%files
%defattr(-,root,root)
%license LICENSE
%{_sysconfdir}/rc.d/init.d/openldap
%{_sysconfdir}/openldap/slapd.conf
%{_sysconfdir}/openldap/initial_config.ldif
%{_datadir}/starlingx/slapd.service
%{_datadir}/starlingx/slapd.sysconfig
