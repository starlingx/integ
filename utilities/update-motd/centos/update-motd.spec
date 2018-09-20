Name: update-motd
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
Summary: dynamic MOTD generation

Group: base
License: Apache-2.0
URL: unknown
Source0: motd-footer
Source1: motd-header
Source2: motd-update
Source3: motd-update.cron
Source4: customize-banner
Source5: apply_banner_customization
Source6: install_banner_customization
Source7: LICENSE
Source8: motd.head

Requires: crontabs

%description
dynamic MOTD generation

%prep


%build


%install
install -d %{buildroot}%{_sbindir}
install -m 700 %{SOURCE2} %{buildroot}%{_sbindir}/motd-update

install -d %{buildroot}%{_sysconfdir}

install -d %{buildroot}%{_sysconfdir}/motd.d
install -m 755 %{SOURCE1} %{buildroot}%{_sysconfdir}/motd.d/00-header
install -m 755 %{SOURCE0} %{buildroot}%{_sysconfdir}/motd.d/99-footer
install -m 644 %{SOURCE8} %{buildroot}%{_sysconfdir}/motd.head

install -d %{buildroot}%{_sysconfdir}/cron.d
install -m 600 %{SOURCE3} %{buildroot}%{_sysconfdir}/cron.d/motd-update
install -m 700 %{SOURCE4} %{buildroot}%{_sbindir}/customize-banner
install -m 700 %{SOURCE5} %{buildroot}%{_sbindir}/apply_banner_customization
install -m 700 %{SOURCE6} %{buildroot}%{_sbindir}/install_banner_customization


%files
%license ../SOURCES/LICENSE
%dir %{_sysconfdir}/motd.d/
%{_sysconfdir}/motd.d/*
/usr/sbin/*
/etc/motd.d/*
%{_sysconfdir}/motd.head
/etc/cron.d/*
%{_sbindir}/motd-update
%{_sbindir}/customize-banner
%{_sbindir}/apply_banner_customization
%{_sbindir}/install_banner_customization

%changelog

