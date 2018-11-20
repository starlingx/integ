Summary: StarlingX lighttpd Configuration File
Name: lighttpd-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: config-files
Packager: StarlingX
URL: unknown
Source: %name-%version.tar.gz

BuildArch: noarch
Requires: lighttpd

%define debug_package %{nil}

%description
StarlingX lighttpd configuration file

%prep

%setup

%build

%install

CONFDIR=%{buildroot}%{_sysconfdir}/lighttpd
ROOTDIR=%{buildroot}/www

install -d -m 1777 ${ROOTDIR}/tmp
install -d ${CONFDIR}/ssl
install -d ${ROOTDIR}/pages/dav
install -d %{buildroot}%{_datadir}/starlingx
install -m640 lighttpd.conf %{buildroot}%{_datadir}/starlingx/lighttpd.conf
install -m755 lighttpd.init %{buildroot}%{_datadir}/starlingx/lighttpd.init
install -m644 lighttpd-inc.conf ${CONFDIR}/lighttpd-inc.conf
install -m644 index.html.lighttpd ${ROOTDIR}/pages/index.html

install -d %{buildroot}%{_sysconfdir}/logrotate.d
install -m644 lighttpd.logrotate %{buildroot}%{_datadir}/starlingx/lighttpd.logrotate

chmod 02770 %{buildroot}%{_sysconfdir}/lighttpd

%post
if [ $1 -eq 1 ] ; then
    cp -f %{_datadir}/starlingx/lighttpd.conf %{_sysconfdir}/lighttpd/lighttpd.conf
    chmod 640 %{_sysconfdir}/lighttpd/lighttpd.conf
    cp -f %{_datadir}/starlingx/lighttpd.init %{_sysconfdir}/rc.d/init.d/lighttpd
    chmod 755 %{_sysconfdir}/rc.d/init.d/lighttpd
    cp -f %{_datadir}/starlingx/lighttpd.logrotate %{_sysconfdir}/logrotate.d/lighttpd
    chmod 644 %{_sysconfdir}/logrotate.d/lighttpd
fi


%files
%defattr(-,root,root)
%license LICENSE
%{_datadir}/starlingx/lighttpd.conf
%{_datadir}/starlingx/lighttpd.logrotate
%{_datadir}/starlingx/lighttpd.init
%dir /www/pages/
/www/pages/*
%config(noreplace) %{_sysconfdir}/lighttpd/lighttpd-inc.conf
/www/pages/index.html
