Summary: Host performance data collection tools package
Name: engtools
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: Tools
Packager: Wind River <info@windriver.com>
URL: http://www.windriver.com/
BuildArch: noarch
Source: %{name}-%{version}.tar.gz

BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

Requires: iperf3

%description
This package contains data collection tools to monitor host performance.
Tools are general purpose engineering and debugging related. Includes
overall memory, cpu occupancy, per-task cpu, per-task scheduling, per-task
io.

# Don't try fancy stuff like debuginfo, which is useless on binary-only
# packages. Don't strip binary too
# Be sure buildpolicy set to do nothing
%define        __spec_install_post %{nil}
%define          debug_package %{nil}
%define        __os_install_post %{_dbpath}/brp-compress
%define _binaries_in_noarch_packages_terminate_build   0

%define local_dir /usr/local
%define local_bindir %{local_dir}/bin/
%define local_initdir /etc/init.d/
%define local_confdir /etc/engtools/
%define local_systemddir /etc/systemd/system/

%prep
%setup -q							

%build
# Empty section.

%install
mkdir -p %{buildroot}
install -d 755 %{buildroot}%{local_bindir}
# Installing additional tools, memtop, occtop and schedtop are already in the image
install -m 755 buddyinfo.py %{buildroot}%{local_bindir}
install -m 755 chewmem %{buildroot}%{local_bindir}
# Installing data collection scripts
install -m 755 ceph.sh %{buildroot}%{local_bindir}
install -m 755 cleanup-engtools.sh %{buildroot}%{local_bindir}
install -m 755 collect-engtools.sh %{buildroot}%{local_bindir}
install -m 755 diskstats.sh %{buildroot}%{local_bindir}
install -m 755 engtools_util.sh %{buildroot}%{local_bindir}
install -m 755 filestats.sh %{buildroot}%{local_bindir}
install -m 755 iostat.sh %{buildroot}%{local_bindir}
install -m 755 linux_benchmark.sh %{buildroot}%{local_bindir}
install -m 755 memstats.sh %{buildroot}%{local_bindir}
install -m 755 netstats.sh %{buildroot}%{local_bindir}
install -m 755 postgres.sh %{buildroot}%{local_bindir}
install -m 755 rabbitmq.sh %{buildroot}%{local_bindir}
install -m 755 remote/rbzip2-engtools.sh %{buildroot}%{local_bindir}
install -m 755 remote/rstart-engtools.sh %{buildroot}%{local_bindir} 
install -m 755 remote/rstop-engtools.sh %{buildroot}%{local_bindir} 
install -m 755 remote/rsync-engtools-data.sh %{buildroot}%{local_bindir}
install -m 755 slab.sh %{buildroot}%{local_bindir}
install -m 755 ticker.sh %{buildroot}%{local_bindir}
install -m 755 top.sh %{buildroot}%{local_bindir}
install -m 755 vswitch.sh %{buildroot}%{local_bindir}
install -m 755 live_stream.py %{buildroot}%{local_bindir}
# Installing conf file
install -d 755 %{buildroot}%{local_confdir}
install -m 644 -p -D cfg/engtools.conf %{buildroot}%{local_confdir}
# Installing init script
install -d 755 %{buildroot}%{local_initdir}
install -m 755 init.d/collect-engtools.sh %{buildroot}%{local_initdir}
# Installing service file
install -d 755 %{buildroot}%{local_systemddir}
install -m 644 -p -D collect-engtools.service %{buildroot}%{local_systemddir}

%clean
rm -rf $RPM_BUILD_ROOT

%files
%license LICENSE
%defattr(-,root,root,-)
%{local_bindir}/*
%{local_confdir}/*
%{local_initdir}/*
%{local_systemddir}/*

%post
/bin/systemctl enable collect-engtools.service > /dev/null 2>&1
/bin/systemctl start collect-engtools.service > /dev/null 2>&1

%preun
#/bin/systemctl --no-reload disable collect-engtools.sh.service > /dev/null 2>&1
#/bin/systemctl stop collect-engtools.sh.service > /dev/null 2>&1
%systemd_preun collect-engtools.service

%postun
%systemd_postun_with_restart collect-engtools.service
