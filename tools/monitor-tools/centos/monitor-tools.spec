Summary: Monitor tools package
Name: monitor-tools
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Requires: initscripts-config

%description
This package contains data collection tools to monitor host performance.
Tools are general purpose engineering and debugging related. Includes
overall memory, cpu occupancy, per-task cpu, per-task scheduling, per-task
io.

%prep
%autosetup

%install
rm -rf $RPM_BUILD_ROOT 
%global _buildsubdir %{_builddir}/%{name}-%{version}
install -d %{buildroot}/usr/bin
install %{_buildsubdir}/memtop %{buildroot}/usr/bin
install %{_buildsubdir}/schedtop %{buildroot}/usr/bin
install %{_buildsubdir}/occtop %{buildroot}/usr/bin

%files
%license LICENSE
%defattr(-,root,root,-)
/usr/bin/*

%post
grep schedstats /etc/sysctl.conf
if [ $? -ne 0 ]; then
  echo -e "\nkernel.sched_schedstats=1" >> /etc/sysctl.conf
  sysctl -p &>/dev/null
fi
exit 0
