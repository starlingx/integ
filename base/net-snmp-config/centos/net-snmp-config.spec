Summary: net-snmp-config
Name: net-snmp-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Requires: net-snmp
Summary: package StarlingX configuration files of net-snmp to system folder.

%description
package StarlingX configuration files of net-snmp to system folder.

%prep
%setup

%build

%install
%{__install} -d %{buildroot}%{_datadir}/starlingx
%{__install} -d %{buildroot}%{_datadir}/snmp
%{__install} -d %{buildroot}%{_initrddir}
%{__install} -d  %{buildroot}%{_sysconfdir}/systemd/system

%{__install} -m 644 stx.snmpd.conf    %{buildroot}%{_datadir}/starlingx/stx.snmpd.conf
%{__install} -m 755 stx.snmpd         %{buildroot}%{_initddir}/snmpd
%{__install} -m 660 stx.snmp.conf     %{buildroot}%{_datadir}/snmp/snmp.conf
%{__install} -m 644 snmpd.service     %{buildroot}%{_sysconfdir}/systemd/system/snmpd.service

%post
if [ $1 -eq 1 ] ; then
        # Initial installation
        cp -f %{_datadir}/starlingx/stx.snmpd.conf   %{_sysconfdir}/snmp/snmpd.conf
        chmod 640 %{_sysconfdir}/snmp/snmpd.conf
        chmod 640 %{_sysconfdir}/snmp/snmptrapd.conf
fi
%{_bindir}/systemctl disable snmpd.service

%files
%{_datadir}/starlingx/stx.snmpd.conf
%{_initddir}/snmpd
%config(noreplace) %attr(0660,snmpd,snmpd) %{_datadir}/snmp/snmp.conf
%{_sysconfdir}/systemd/system/snmpd.service

