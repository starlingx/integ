Summary: CGCS Platform Data Collection Scripts Package
Name: collector
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown
Source0: %{name}-%{version}.tar.gz

%description
This packages scripts that implement data and log collection that field
support can execute to gather current state and runtime history for off
platform analysis and debug.

%prep
%setup

%install
mkdir -p %{buildroot}

install -d 755 -d %{buildroot}%{_sysconfdir}/collect.d
install -d 755 -d %{buildroot}%{_sysconfdir}/collect
install -d 755 -d %{buildroot}/usr/local/sbin
install -d 755 -d %{buildroot}/usr/local/bin
install -d 755 -d %{buildroot}%{_sbindir}

install -m 755 collect %{buildroot}/usr/local/sbin/collect
install -m 755 collect_host %{buildroot}/usr/local/sbin/collect_host
install -m 755 collect_date %{buildroot}/usr/local/sbin/collect_date
install -m 755 collect_utils %{buildroot}/usr/local/sbin/collect_utils
install -m 755 collect_parms %{buildroot}/usr/local/sbin/collect_parms
install -m 755 collect_mask_passwords %{buildroot}/usr/local/sbin/collect_mask_passwords
install -m 755 expect_done %{buildroot}/usr/local/sbin/expect_done

install -m 755 collect_sysinv.sh %{buildroot}%{_sysconfdir}/collect.d/collect_sysinv
install -m 755 collect_psqldb.sh %{buildroot}%{_sysconfdir}/collect.d/collect_psqldb
install -m 755 collect_openstack.sh %{buildroot}%{_sysconfdir}/collect.d/collect_openstack
install -m 755 collect_networking.sh %{buildroot}%{_sysconfdir}/collect.d/collect_networking
install -m 755 collect_ceph.sh %{buildroot}%{_sysconfdir}/collect.d/collect_ceph
install -m 755 collect_sm.sh %{buildroot}%{_sysconfdir}/collect.d/collect_sm
install -m 755 collect_tc.sh %{buildroot}%{_sysconfdir}/collect.d/collect_tc
install -m 755 collect_nfv_vim.sh %{buildroot}%{_sysconfdir}/collect.d/collect_nfv_vim
install -m 755 collect_vswitch.sh %{buildroot}%{_sysconfdir}/collect.d/collect_vswitch
install -m 755 collect_patching.sh %{buildroot}%{_sysconfdir}/collect.d/collect_patching
install -m 755 collect_coredump.sh %{buildroot}%{_sysconfdir}/collect.d/collect_coredump
install -m 755 collect_crash.sh %{buildroot}%{_sysconfdir}/collect.d/collect_crash
install -m 755 collect_ima.sh %{buildroot}%{_sysconfdir}/collect.d/collect_ima

install -m 755 etc.exclude %{buildroot}%{_sysconfdir}/collect/etc.exclude
install -m 755 run.exclude %{buildroot}%{_sysconfdir}/collect/run.exclude

ln -sf /usr/local/sbin/collect %{buildroot}/usr/local/bin/collect
ln -sf /usr/local/sbin/collect %{buildroot}%{_sbindir}/collect

%clean
rm -rf %{buildroot}

%files
%license LICENSE
%defattr(-,root,root,-)
%{_sysconfdir}/collect/*
%{_sysconfdir}/collect.d/*
/usr/local/sbin/*
/usr/local/bin/collect
%{_sbindir}/collect
