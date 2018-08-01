Summary: CGCS IO Scheduler Configuration
Name: io-scheduler
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown

Source0: 60-io-scheduler.rules
Source1: LICENSE

%define udev_rules_d %{_sysconfdir}/udev/rules.d

%description
CGCS io scheduler configuration and tuning.

%install
mkdir -p %{buildroot}%{udev_rules_d}
install -m 644 %{SOURCE0} %{buildroot}%{udev_rules_d}/60-io-scheduler.rules

%post
/bin/udevadm control --reload-rules
/bin/udevadm trigger --type=devices --subsystem-match=block

%files
%license ../SOURCES/LICENSE
%defattr(-,root,root,-)
%{_sysconfdir}/udev/rules.d
