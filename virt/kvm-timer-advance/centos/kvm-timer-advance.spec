Summary: StarlingX KVM Timer Advance Package
Name: kvm-timer-advance
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: GPLv2
Group: base
Packager: StarlingX
URL: unknown

Source: %name-%version.tar.gz

BuildArch: noarch

BuildRequires: systemd-devel

Requires: qemu-kvm-tools-ev
Requires: systemd


%description
StarlingX KVM Timer Advance Package

%define debug_package %{nil}

%prep

%setup

%build

%install
install -d -m 755 %{buildroot}%{_sysconfdir}/%{name}
install -p -D -m 755 setup_kvm_timer_advance.sh %{buildroot}%{_bindir}/setup_kvm_timer_advance.sh
install -p -D -m 444 kvm_timer_advance_setup.service %{buildroot}%{_unitdir}/kvm_timer_advance_setup.service

%files
%defattr(-,root,root,-)
%doc LICENSE
%{_bindir}/setup_kvm_timer_advance.sh
%{_unitdir}/kvm_timer_advance_setup.service
%dir %{_sysconfdir}/%{name}
