# Uncomment these for snapshot releases:
# commit0 is the git sha of the last commit
# date is the date YYYYMMDD of the snapshot
#%%global commit0 bd916d13dbb845746983a6780da772154df647ba
#%%global date 20180219
%global shortcommit0 %(c=%{commit0}; echo ${c:0:7})

# If wants to run tests while building, specify the '--with check'
# option. For example:
# rpmbuild -bb --with check openvswitch.spec

# Enable PIE, bz#955181
%global _hardened_build 1

# RHEL-7 doesn't define _rundir macro yet
# Fedora 15 onwards uses /run as _rundir
%if 0%{!?_rundir:1}
%define _rundir /run
%endif

# To disable DPDK support, specify '--without dpdk' when building
%bcond_without dpdk

# test-suite is broken for big endians
# https://bugzilla.redhat.com/show_bug.cgi?id=1105458#c10
# "ofproto-dpif - select group with dp_hash selection method" test is broken on armv7lh
%ifarch x86_64 aarch64 ppc64le
%bcond_with check
%else
%bcond_with check
%endif
# option to run kernel datapath tests, requires building as root!
%bcond_with check_datapath_kernel
# option to build with libcap-ng, needed for running OVS as regular user
%bcond_without libcapng
# option to build openvswitch-ovn-docker package
%bcond_with ovn_docker

%if 0%{?fedora}
%global with_python3 1
%endif

Name: openvswitch
Summary: Open vSwitch daemon/database/utilities
URL: http://www.openvswitch.org/
# Carried over from 2.6.1 CBS builds, introduced to win over 2.6.90
Epoch:   1
Version: 2.11.0
Release: 0%{?_tis_dist}.%{tis_patch_ver}

# Nearly all of openvswitch is ASL 2.0.  The bugtool is LGPLv2+, and the
# lib/sflow*.[ch] files are SISSL
# datapath/ is GPLv2 (although not built into any of the binary packages)
License: ASL 2.0 and LGPLv2+ and SISSL

%define dpdkver 18.11
%define dpdkdir dpdk
%define dpdksver %(echo %{dpdkver} | cut -d. -f-2)
# NOTE: DPDK does not currently build for s390x
%define dpdkarches x86_64 aarch64 ppc64le

%if 0%{?commit0:1}
Source: https://github.com/openvswitch/ovs/archive/%{commit0}.tar.gz#/%{name}-%{shortcommit0}.tar.gz
%else
Source: http://openvswitch.org/releases/%{name}-%{version}.tar.gz
%endif
Source10: http://fast.dpdk.org/rel/dpdk-%{dpdkver}.tar.xz

Source500: configlib.sh
Source501: gen_config_group.sh
Source502: set_config.sh

Source506: x86_64-native-linuxapp-gcc-config

# The DPDK is designed to optimize througput of network traffic using, among
# other techniques, carefully crafted assembly instructions.  As such it
# needs extensive work to port it to other architectures.
ExclusiveArch: x86_64 aarch64 ppc64le s390x

# dpdk_mach_arch maps between rpm and dpdk arch name, often same as _target_cpu
# dpdk_mach_tmpl is the config template dpdk_mach name, often "native"
# dpdk_mach is the actual dpdk_mach name used in the dpdk make system
%ifarch x86_64
%define dpdk_mach_arch x86_64
%define dpdk_mach_tmpl native
%define dpdk_mach default
%endif

%define dpdktarget %{dpdk_mach_arch}-%{dpdk_mach_tmpl}-linuxapp-gcc

# ovs-patches
Patch01: run-services-as-root-user.patch

BuildRequires: gcc
BuildRequires: python2-sphinx
BuildRequires: autoconf automake libtool
BuildRequires: systemd-units openssl openssl-devel
BuildRequires: python2-devel python2-six
%if 0%{?with_python3}
BuildRequires: python3-devel python3-six
%endif
BuildRequires: desktop-file-utils
BuildRequires: groff-base graphviz
# make check dependencies
BuildRequires: procps-ng
BuildRequires: python2-pyOpenSSL
%if %{with check_datapath_kernel}
BuildRequires: nmap-ncat
# would be useful but not available in RHEL or EPEL
#BuildRequires: python2-pyftpdlib
%endif

%if %{with libcapng}
BuildRequires: libcap-ng libcap-ng-devel
%endif

%if %{with dpdk}
%ifarch %{dpdkarches}
# DPDK driver dependencies
BuildRequires: zlib-devel libpcap-devel numactl-devel
BuildRequires: rdma-core-devel
BuildRequires:  libmnl-devel
Requires: python-pyelftools

# Virtual provide for depending on DPDK-enabled OVS
Provides: openvswitch-dpdk = %{version}-%{release}
# Migration path for openvswitch-dpdk package
Obsoletes: openvswitch-dpdk < 2.6.0
# Required by packaging policy for the bundled DPDK
Provides: bundled(dpdk) = %{dpdkver}
%endif
%endif

Requires: openssl iproute module-init-tools
#Upstream kernel commit 4f647e0a3c37b8d5086214128614a136064110c3
#Requires: kernel >= 3.15.0-0

Requires(post): /usr/bin/getent
Requires(post): /usr/sbin/useradd
Requires(post): /bin/sed
Requires(post): /usr/sbin/usermod
Requires(post): /usr/sbin/groupadd
Requires(post): systemd-units
Requires(preun): systemd-units
Requires(postun): systemd-units
Obsoletes: openvswitch-controller <= 0:2.1.0-1

%description
Open vSwitch provides standard network bridging functions and
support for the OpenFlow protocol for remote per-flow control of
traffic.

%package -n python2-openvswitch
Summary: Open vSwitch python2 bindings
License: ASL 2.0
BuildArch: noarch
Requires: python2 python2-six
Obsoletes: python-openvswitch < %{epoch}:2.7.2
Provides: python-openvswitch = %{epoch}:%{version}-%{release}

%description -n python2-openvswitch
Python bindings for the Open vSwitch database

%if 0%{?with_python3}
%package -n python3-openvswitch
Summary: Open vSwitch python3 bindings
License: ASL 2.0
BuildArch: noarch
Requires: python3 python3-six

%description -n python3-openvswitch
Python bindings for the Open vSwitch database
%endif

%package test
Summary: Open vSwitch testing utilities
License: ASL 2.0
BuildArch: noarch
Requires: python2-openvswitch = %{epoch}:%{version}-%{release}
Requires: python2 python2-twisted

%description test
Utilities that are useful to diagnose performance and connectivity
issues in Open vSwitch setup.

%package devel
Summary: Open vSwitch OpenFlow development package (library, headers)
License: ASL 2.0
Provides: openvswitch-static = %{epoch}:%{version}-%{release}

%description devel
This provides static library, libopenswitch.a and the openvswitch header
files needed to build an external application.

%package ovn-central
Summary: Open vSwitch - Open Virtual Network support
License: ASL 2.0
Requires: openvswitch openvswitch-ovn-common
Requires: firewalld-filesystem

%description ovn-central
OVN, the Open Virtual Network, is a system to support virtual network
abstraction.  OVN complements the existing capabilities of OVS to add
native support for virtual network abstractions, such as virtual L2 and L3
overlays and security groups.

%package ovn-host
Summary: Open vSwitch - Open Virtual Network support
License: ASL 2.0
Requires: openvswitch openvswitch-ovn-common
Requires: firewalld-filesystem

%description ovn-host
OVN, the Open Virtual Network, is a system to support virtual network
abstraction.  OVN complements the existing capabilities of OVS to add
native support for virtual network abstractions, such as virtual L2 and L3
overlays and security groups.

%package ovn-vtep
Summary: Open vSwitch - Open Virtual Network support
License: ASL 2.0
Requires: openvswitch openvswitch-ovn-common

%description ovn-vtep
OVN vtep controller

%package ovn-common
Summary: Open vSwitch - Open Virtual Network support
License: ASL 2.0
Requires: openvswitch

%description ovn-common
Utilities that are use to diagnose and manage the OVN components.

%if %{with ovn_docker}
%package ovn-docker
Summary: Open vSwitch - Open Virtual Network support
License: ASL 2.0
Requires: openvswitch openvswitch-ovn-common python2-openvswitch

%description ovn-docker
Docker network plugins for OVN.
%endif

%prep
%if 0%{?commit0:1}
%autosetup -n ovs-%{commit0} -a 10 -p 1
%else
%autosetup -a 10 -p 1
%endif

%build
%if 0%{?commit0:1}
# fix the snapshot unreleased version to be the released one.
sed -i.old -e "s/^AC_INIT(openvswitch,.*,/AC_INIT(openvswitch, %{version},/" configure.ac
%endif
./boot.sh

%if %{with dpdk}
%ifarch %{dpdkarches}    # build dpdk
# Lets build DPDK first
cd %{dpdkdir}-%{dpdkver}

# In case dpdk-devel is installed
unset RTE_SDK RTE_INCLUDE RTE_TARGET

# Avoid appending second -Wall to everything, it breaks upstream warning
# disablers in makefiles. Strip explicit -march= from optflags since they
# will only guarantee build failures, DPDK is picky with that.
export EXTRA_CFLAGS="$(echo %{optflags} | sed -e 's:-Wall::g' -e 's:-march=[[:alnum:]]* ::g') -Wformat -fPIC"

# DPDK defaults to using builder-specific compiler flags.  However,
# the config has been changed by specifying CONFIG_RTE_MACHINE=default
# in order to build for a more generic host.  NOTE: It is possible that
# the compiler flags used still won't work for all Fedora-supported
# machines, but runtime checks in DPDK will catch those situations.

make V=1 O=%{dpdktarget} T=%{dpdktarget} %{?_smp_mflags} config

cp -f %{SOURCE500} %{SOURCE502} "%{_sourcedir}/%{dpdktarget}-config" .
%{SOURCE502} %{dpdktarget}-config "%{dpdktarget}/.config"

make V=1 O=%{dpdktarget} %{?_smp_mflags}

# Generate a list of supported drivers, its hard to tell otherwise.
cat << EOF > README.DPDK-PMDS
DPDK drivers included in this package:

EOF

for f in $(ls %{dpdk_mach_arch}-%{dpdk_mach_tmpl}-linuxapp-gcc/lib/lib*_pmd_*); do
    basename ${f} | cut -c12- | cut -d. -f1 | tr [:lower:] [:upper:]
done >> README.DPDK-PMDS

cat << EOF >> README.DPDK-PMDS

For further information about the drivers, see
http://dpdk.org/doc/guides-%{dpdksver}/nics/index.html
EOF

cd -
%endif    # build dpdk
%endif

# And now for OVS...
%configure \
%if %{with libcapng}
        --enable-libcapng \
%else
        --disable-libcapng \
%endif
  --enable-ssl \
%if %{with dpdk}
%ifarch %{dpdkarches}
  --with-dpdk=$(pwd)/%{dpdkdir}-%{dpdkver}/%{dpdktarget} \
%endif
%endif
  --with-pkidir=%{_sharedstatedir}/openvswitch/pki \
  PYTHON=/usr/bin/python2
/usr/bin/python2 build-aux/dpdkstrip.py \
        --dpdk \
        < rhel/usr_lib_systemd_system_ovs-vswitchd.service.in \
        > rhel/usr_lib_systemd_system_ovs-vswitchd.service
make %{?_smp_mflags} \
%if %{with dpdk}
%ifarch %{dpdkarches}
  LDFLAGS="-libverbs -lmlx4 -lmlx5"
%endif
%endif

%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT

install -d -m 0755 $RPM_BUILD_ROOT%{_rundir}/openvswitch
install -d -m 0750 $RPM_BUILD_ROOT%{_localstatedir}/log/openvswitch
install -d -m 0755 $RPM_BUILD_ROOT%{_sysconfdir}/openvswitch

install -p -D -m 0644 rhel/usr_lib_udev_rules.d_91-vfio.rules \
        $RPM_BUILD_ROOT%{_udevrulesdir}/91-vfio.rules

install -p -D -m 0644 \
        rhel/usr_share_openvswitch_scripts_systemd_sysconfig.template \
        $RPM_BUILD_ROOT/%{_sysconfdir}/sysconfig/openvswitch

for service in openvswitch ovsdb-server ovs-vswitchd ovs-delete-transient-ports \
                ovn-controller ovn-controller-vtep ovn-northd; do
        install -p -D -m 0644 \
                        rhel/usr_lib_systemd_system_${service}.service \
                        $RPM_BUILD_ROOT%{_unitdir}/${service}.service
done

install -m 0755 rhel/etc_init.d_openvswitch \
        $RPM_BUILD_ROOT%{_datadir}/openvswitch/scripts/openvswitch.init

install -p -D -m 0644 rhel/etc_openvswitch_default.conf \
        $RPM_BUILD_ROOT/%{_sysconfdir}/openvswitch/default.conf

install -p -D -m 0644 rhel/etc_logrotate.d_openvswitch \
        $RPM_BUILD_ROOT/%{_sysconfdir}/logrotate.d/openvswitch

install -m 0644 vswitchd/vswitch.ovsschema \
        $RPM_BUILD_ROOT/%{_datadir}/openvswitch/vswitch.ovsschema

install -d -m 0755 $RPM_BUILD_ROOT/%{_sysconfdir}/sysconfig/network-scripts/
install -p -m 0755 rhel/etc_sysconfig_network-scripts_ifdown-ovs \
        $RPM_BUILD_ROOT/%{_sysconfdir}/sysconfig/network-scripts/ifdown-ovs
install -p -m 0755 rhel/etc_sysconfig_network-scripts_ifup-ovs \
        $RPM_BUILD_ROOT/%{_sysconfdir}/sysconfig/network-scripts/ifup-ovs

install -d -m 0755 $RPM_BUILD_ROOT%{python2_sitelib}
cp -a $RPM_BUILD_ROOT/%{_datadir}/openvswitch/python/* \
   $RPM_BUILD_ROOT%{python2_sitelib}
%if 0%{?with_python3}
install -d -m 0755 $RPM_BUILD_ROOT%{python3_sitelib}
cp -a $RPM_BUILD_ROOT/%{_datadir}/openvswitch/python/ovs \
   $RPM_BUILD_ROOT%{python3_sitelib}
%endif
rm -rf $RPM_BUILD_ROOT/%{_datadir}/openvswitch/python/

install -d -m 0755 $RPM_BUILD_ROOT/%{_sharedstatedir}/openvswitch

install -d -m 0755 $RPM_BUILD_ROOT%{_prefix}/lib/firewalld/services/
install -p -m 0644 rhel/usr_lib_firewalld_services_ovn-central-firewall-service.xml \
        $RPM_BUILD_ROOT%{_prefix}/lib/firewalld/services/ovn-central-firewall-service.xml
install -p -m 0644 rhel/usr_lib_firewalld_services_ovn-host-firewall-service.xml \
        $RPM_BUILD_ROOT%{_prefix}/lib/firewalld/services/ovn-host-firewall-service.xml

install -d -m 0755 $RPM_BUILD_ROOT%{_prefix}/lib/ocf/resource.d/ovn
ln -s %{_datadir}/openvswitch/scripts/ovndb-servers.ocf \
      $RPM_BUILD_ROOT%{_prefix}/lib/ocf/resource.d/ovn/ovndb-servers

install -p -D -m 0755 \
        rhel/usr_share_openvswitch_scripts_ovs-systemd-reload \
        $RPM_BUILD_ROOT%{_datadir}/openvswitch/scripts/ovs-systemd-reload

touch $RPM_BUILD_ROOT%{_sysconfdir}/openvswitch/conf.db
touch $RPM_BUILD_ROOT%{_sysconfdir}/openvswitch/system-id.conf

%if %{with dpdk}
%ifarch %{dpdkarches}
  install -m 0755 %{dpdkdir}-%{dpdkver}/usertools/dpdk-pmdinfo.py $RPM_BUILD_ROOT%{_datadir}/openvswitch/scripts/dpdk-pmdinfo.py
  install -m 0755 %{dpdkdir}-%{dpdkver}/usertools/dpdk-devbind.py $RPM_BUILD_ROOT%{_datadir}/openvswitch/scripts/dpdk-devbind.py
%endif
%endif

# remove unpackaged files
rm -f $RPM_BUILD_ROOT/%{_bindir}/ovs-benchmark \
        $RPM_BUILD_ROOT/%{_bindir}/ovs-docker \
        $RPM_BUILD_ROOT/%{_bindir}/ovs-parse-backtrace \
        $RPM_BUILD_ROOT/%{_bindir}/ovs-testcontroller \
        $RPM_BUILD_ROOT/%{_sbindir}/ovs-vlan-bug-workaround \
        $RPM_BUILD_ROOT/%{_mandir}/man1/ovs-benchmark.1* \
        $RPM_BUILD_ROOT/%{_mandir}/man8/ovs-testcontroller.* \
        $RPM_BUILD_ROOT/%{_mandir}/man8/ovs-vlan-bug-workaround.8*

%if %{without ovn_docker}
rm -f $RPM_BUILD_ROOT/%{_bindir}/ovn-docker-overlay-driver \
        $RPM_BUILD_ROOT/%{_bindir}/ovn-docker-underlay-driver
%endif

%check
%if %{with check}
    if make check TESTSUITEFLAGS='%{_smp_mflags}' ||
       make check TESTSUITEFLAGS='--recheck'; then :;
    else
        cat tests/testsuite.log
        exit 1
    fi
%endif
%if %{with check_datapath_kernel}
    if make check-kernel RECHECK=yes; then :;
    else
        cat tests/system-kmod-testsuite.log
        exit 1
    fi
%endif

%clean
rm -rf $RPM_BUILD_ROOT

%preun
%if 0%{?systemd_preun:1}
    %systemd_preun %{name}.service
%else
    if [ $1 -eq 0 ] ; then
    # Package removal, not upgrade
        /bin/systemctl --no-reload disable %{name}.service >/dev/null 2>&1 || :
        /bin/systemctl stop %{name}.service >/dev/null 2>&1 || :
    fi
%endif

%preun ovn-central
%if 0%{?systemd_preun:1}
    %systemd_preun ovn-northd.service
%else
    if [ $1 -eq 0 ] ; then
        # Package removal, not upgrade
        /bin/systemctl --no-reload disable ovn-northd.service >/dev/null 2>&1 || :
        /bin/systemctl stop ovn-northd.service >/dev/null 2>&1 || :
    fi
%endif

%preun ovn-host
%if 0%{?systemd_preun:1}
    %systemd_preun ovn-controller.service
%else
    if [ $1 -eq 0 ] ; then
        # Package removal, not upgrade
        /bin/systemctl --no-reload disable ovn-controller.service >/dev/null 2>&1 || :
        /bin/systemctl stop ovn-controller.service >/dev/null 2>&1 || :
    fi
%endif

%preun ovn-vtep
%if 0%{?systemd_preun:1}
    %systemd_preun ovn-controller-vtep.service
%else
    if [ $1 -eq 0 ] ; then
        # Package removal, not upgrade
        /bin/systemctl --no-reload disable ovn-controller-vtep.service >/dev/null 2>&1 || :
        /bin/systemctl stop ovn-controller-vtep.service >/dev/null 2>&1 || :
    fi
%endif

%if 0%{?systemd_post:1}
    %systemd_post %{name}.service
%else
    # Package install, not upgrade
    if [ $1 -eq 1 ]; then
        /bin/systemctl daemon-reload >dev/null || :
    fi
%endif

%post ovn-central
%if 0%{?systemd_post:1}
    %systemd_post ovn-northd.service
%else
    # Package install, not upgrade
    if [ $1 -eq 1 ]; then
        /bin/systemctl daemon-reload >dev/null || :
    fi
%endif

%post ovn-host
%if 0%{?systemd_post:1}
    %systemd_post ovn-controller.service
%else
    # Package install, not upgrade
    if [ $1 -eq 1 ]; then
        /bin/systemctl daemon-reload >dev/null || :
    fi
%endif

%post ovn-vtep
%if 0%{?systemd_post:1}
    %systemd_post ovn-controller-vtep.service
%else
    # Package install, not upgrade
    if [ $1 -eq 1 ]; then
        /bin/systemctl daemon-reload >dev/null || :
    fi
%endif
%postun ovn-central
%if 0%{?systemd_postun_with_restart:1}
    %systemd_postun_with_restart ovn-northd.service
%else
    /bin/systemctl daemon-reload >/dev/null 2>&1 || :
    if [ "$1" -ge "1" ] ; then
    # Package upgrade, not uninstall
        /bin/systemctl try-restart ovn-northd.service >/dev/null 2>&1 || :
    fi
%endif

%postun ovn-host
%if 0%{?systemd_postun_with_restart:1}
    %systemd_postun_with_restart ovn-controller.service
%else
    /bin/systemctl daemon-reload >/dev/null 2>&1 || :
    if [ "$1" -ge "1" ] ; then
        # Package upgrade, not uninstall
        /bin/systemctl try-restart ovn-controller.service >/dev/null 2>&1 || :
    fi
%endif

%postun ovn-vtep
%if 0%{?systemd_postun_with_restart:1}
    %systemd_postun_with_restart ovn-controller-vtep.service
%else
    /bin/systemctl daemon-reload >/dev/null 2>&1 || :
    if [ "$1" -ge "1" ] ; then
        # Package upgrade, not uninstall
        /bin/systemctl try-restart ovn-controller-vtep.service >/dev/null 2>&1 || :
    fi
%endif

%postun
%if 0%{?systemd_postun:1}
    %systemd_postun %{name}.service
%else
    /bin/systemctl daemon-reload >/dev/null 2>&1 || :
%endif


%files -n python2-openvswitch
%{python2_sitelib}/ovs

%if 0%{?with_python3}
%files -n python3-openvswitch
%{python3_sitelib}/ovs
%endif

%files test
%{_bindir}/ovs-test
%{_bindir}/ovs-vlan-test
%{_bindir}/ovs-l3ping
%{_bindir}/ovs-pcap
%{_bindir}/ovs-tcpdump
%{_bindir}/ovs-tcpundump
%{_mandir}/man8/ovs-test.8*
%{_mandir}/man8/ovs-vlan-test.8*
%{_mandir}/man8/ovs-l3ping.8*
%{_mandir}/man1/ovs-pcap.1*
%{_mandir}/man8/ovs-tcpdump.8*
%{_mandir}/man1/ovs-tcpundump.1*
%{python2_sitelib}/ovstest

%files devel
%{_libdir}/*.a
%{_libdir}/*.la
%{_libdir}/pkgconfig/*.pc
%{_includedir}/openvswitch/*
%{_includedir}/openflow/*
%{_includedir}/ovn/*

%files
%defattr(-,openvswitch,openvswitch)
%verify(not owner group) %dir %{_sysconfdir}/openvswitch
%verify(not owner group) %{_sysconfdir}/openvswitch/default.conf
%config %ghost %verify(not owner group md5 size mtime) %{_sysconfdir}/openvswitch/conf.db
%config %ghost %verify(not owner group md5 size mtime) %{_sysconfdir}/openvswitch/system-id.conf
%config(noreplace) %verify(not owner group md5 size mtime) %{_sysconfdir}/sysconfig/openvswitch
%defattr(-,root,root)
%{_sysconfdir}/bash_completion.d/ovs-appctl-bashcomp.bash
%{_sysconfdir}/bash_completion.d/ovs-vsctl-bashcomp.bash
%config(noreplace) %{_sysconfdir}/logrotate.d/openvswitch
%{_unitdir}/openvswitch.service
%{_unitdir}/ovsdb-server.service
%{_unitdir}/ovs-vswitchd.service
%{_unitdir}/ovs-delete-transient-ports.service
%{_datadir}/openvswitch/scripts/openvswitch.init
%{_sysconfdir}/sysconfig/network-scripts/ifup-ovs
%{_sysconfdir}/sysconfig/network-scripts/ifdown-ovs
%{_datadir}/openvswitch/bugtool-plugins/
%{_datadir}/openvswitch/scripts/ovs-bugtool-*
%{_datadir}/openvswitch/scripts/ovs-check-dead-ifs
%{_datadir}/openvswitch/scripts/ovs-lib
%{_datadir}/openvswitch/scripts/ovs-save
%{_datadir}/openvswitch/scripts/ovs-vtep
%{_datadir}/openvswitch/scripts/ovs-ctl
%{_datadir}/openvswitch/scripts/ovs-kmod-ctl
%{_datadir}/openvswitch/scripts/ovs-monitor-ipsec
%{_datadir}/openvswitch/scripts/ovs-systemd-reload
%{_datadir}/openvswitch/scripts/dpdk-pmdinfo.py
%{_datadir}/openvswitch/scripts/dpdk-devbind.py
%exclude %{_datadir}/openvswitch/scripts/*.py[oc]
%config %{_datadir}/openvswitch/vswitch.ovsschema
%config %{_datadir}/openvswitch/vtep.ovsschema
%{_bindir}/ovs-appctl
%{_bindir}/ovs-dpctl
%{_bindir}/ovs-dpctl-top
%{_bindir}/ovs-ofctl
%{_bindir}/ovs-vsctl
%{_bindir}/ovsdb-client
%{_bindir}/ovsdb-tool
%{_bindir}/ovs-pki
%{_bindir}/vtep-ctl
%{_sbindir}/ovs-bugtool
%{_sbindir}/ovs-vswitchd
%{_sbindir}/ovsdb-server
%{_mandir}/man1/ovsdb-client.1*
%{_mandir}/man1/ovsdb-server.1*
%{_mandir}/man1/ovsdb-tool.1*
%{_mandir}/man5/ovsdb.5*
%{_mandir}/man5/ovsdb-server.5.*
%{_mandir}/man5/ovs-vswitchd.conf.db.5*
%{_mandir}/man5/vtep.5*
%{_mandir}/man7/ovsdb-server.7*
%{_mandir}/man7/ovsdb.7*
%{_mandir}/man7/ovs-actions.7*
%{_mandir}/man7/ovs-fields.7*
%{_mandir}/man8/vtep-ctl.8*
%{_mandir}/man8/ovs-appctl.8*
%{_mandir}/man8/ovs-bugtool.8*
%{_mandir}/man8/ovs-ctl.8*
%{_mandir}/man8/ovs-dpctl.8*
%{_mandir}/man8/ovs-dpctl-top.8*
%{_mandir}/man8/ovs-kmod-ctl.8*
%{_mandir}/man8/ovs-ofctl.8*
%{_mandir}/man8/ovs-pki.8*
%{_mandir}/man8/ovs-vsctl.8*
%{_mandir}/man8/ovs-vswitchd.8*
%{_mandir}/man8/ovs-parse-backtrace.8*
%{_udevrulesdir}/91-vfio.rules
%doc LICENSE NOTICE README.rst NEWS rhel/README.RHEL.rst
%if %{with dpdk}
%ifarch %{dpdkarches}
%doc dpdk-%{dpdkver}/README.DPDK-PMDS
%endif
%endif
/var/lib/openvswitch
%attr(755,-,-) /var/log/openvswitch
%ghost %attr(755,root,root) %{_rundir}/openvswitch

%if %{with ovn_docker}
%files ovn-docker
%{_bindir}/ovn-docker-overlay-driver
%{_bindir}/ovn-docker-underlay-driver
%endif

%files ovn-common
%{_bindir}/ovn-detrace
%{_bindir}/ovn-nbctl
%{_bindir}/ovn-sbctl
%{_bindir}/ovn-trace
%{_datadir}/openvswitch/scripts/ovn-ctl
%{_datadir}/openvswitch/scripts/ovndb-servers.ocf
%{_datadir}/openvswitch/scripts/ovn-bugtool-nbctl-show
%{_datadir}/openvswitch/scripts/ovn-bugtool-sbctl-lflow-list
%{_datadir}/openvswitch/scripts/ovn-bugtool-sbctl-show
%{_mandir}/man1/ovn-detrace.1*
%{_mandir}/man8/ovn-ctl.8*
%{_mandir}/man8/ovn-nbctl.8*
%{_mandir}/man8/ovn-trace.8*
%{_mandir}/man7/ovn-architecture.7*
%{_mandir}/man8/ovn-sbctl.8*
%{_mandir}/man5/ovn-nb.5*
%{_mandir}/man5/ovn-sb.5*
%{_prefix}/lib/ocf/resource.d/ovn/ovndb-servers

%files ovn-central
%{_bindir}/ovn-northd
%{_mandir}/man8/ovn-northd.8*
%config %{_datadir}/openvswitch/ovn-nb.ovsschema
%config %{_datadir}/openvswitch/ovn-sb.ovsschema
%{_unitdir}/ovn-northd.service
%{_prefix}/lib/firewalld/services/ovn-central-firewall-service.xml

%files ovn-host
%{_bindir}/ovn-controller
%{_mandir}/man8/ovn-controller.8*
%{_unitdir}/ovn-controller.service
%{_prefix}/lib/firewalld/services/ovn-host-firewall-service.xml

%files ovn-vtep
%{_bindir}/ovn-controller-vtep
%{_mandir}/man8/ovn-controller-vtep.8*
%{_unitdir}/ovn-controller-vtep.service

%changelog
* Tue Feb 20 2018 Iryna Shcherbina <ishcherb@redhat.com> - 2.9.0-3
- Update Python 2 dependency declarations to new packaging standards
  (See https://fedoraproject.org/wiki/FinalizingFedoraSwitchtoPython3)

* Tue Feb 20 2018 Timothy Redaelli <tredaelli@redhat.com> - 2.9.0-2
- Align totally with RHEL "Fast Datapath" channel 2.9.0-1

* Tue Feb 20 2018 Timothy Redaelli <tredaelli@redhat.com> - 2.9.0-1
- Update to Open vSwitch 2.9.0 and DPDK 17.11
- Align with RHEL "Fast Datapath" channel 2.9.0-1

* Fri Feb 09 2018 Aaron Conole <aconole@redhat.com> - 2.8.1-2
- Update to include 94cd8383e297 and 951d79e638ec from upstream

* Thu Feb 08 2018 Fedora Release Engineering <releng@fedoraproject.org> - 2.8.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Mon Oct 02 2017 Timothy Redaelli <tredaelli@redhat.com> - 2.8.1-1
- Update to Open vSwitch 2.8.1

* Tue Sep 19 2017 Timothy Redaelli <tredaelli@redhat.com> - 2.8.0-2
- Update DPDK to 17.05.2 (bugfixes)

* Mon Sep 04 2017 Timothy Redaelli <tredaelli@redhat.com> - 2.8.0-1
- Update to Open vSwitch 2.8.0 and DPDK 17.05.1 (#1487971)

* Thu Aug 03 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2.7.2-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Thu Jul 27 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2.7.2-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Wed Jul 19 2017 Timothy Redaelli <tredaelli@redhat.com> - 2.7.2-1
- Update to Open vSwitch 2.7.2
- Add a symlink of the OCF script in the OCF resources folder

* Fri Jul 14 2017 Timothy Redaelli <tredaelli@redhat.com> - 2.7.1-2
- Backport fix for CVE-2017-9263 (#1457327)
- Backport fix for CVE-2017-9265 (#1457335)

* Thu Jul 06 2017 Timothy Redaelli <tredaelli@redhat.com> - 2.7.1-1
- Updated to Open vSwitch 2.7.1 and DPDK 16.11.2 (#1468234)

* Tue Jun 13 2017 Timothy Redaelli <tredaelli@redhat.com> - 2.7.0-5
- Backport fix for CVE-2017-9264 (#1457329)

* Wed Jun 07 2017 Timothy Redaelli <tredaelli@redhat.com> - 2.7.0-4
- Remove PYTHONCOERCECLOCALE=0 workaround and backport upstream patch (#1454364)

* Wed May 31 2017 Timothy Redaelli <tredaelli@redhat.com> - 2.7.0-3
- Backport fix for CVE-2017-9214 (#1456797)
- Use %%autosetup instead of %%setup

* Mon May 29 2017 Timothy Redaelli <tredaelli@redhat.com> - 2.7.0-2
- Install OVN firewalld rules

* Thu May 18 2017 Timothy Redaelli <tredaelli@redhat.com> - 2.7.0-1
- Link statically with DPDK 16.11.1 (#1451476)
- Build OVS without DPDK support on all architectures not supported by DPDK
- Added python3-six to BuildRequires in order to launch python3 tests too
- Export PYTHONCOERCECLOCALE=0 in order to workaround an incompatibility
  between Python 3.6.0 (with PEP 538) on Fedora 26+ and testsuite (#1454364)
- Disable tests on armv7hl

* Fri Feb 24 2017 Timothy Redaelli <tredaelli@redhat.com> - 2.7.0-0
- Updated to Open vSwitch 2.7.0 (#1426596)
- Enable DPDK support

* Thu Feb 16 2017 Timothy Redaelli <tredaelli@redhat.com> - 2.6.1-2
- Added python3-openvswitch and renamed python-openvswitch to python2-openvswitch

* Sat Feb 11 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2.6.1-1
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Thu Nov 24 2016 Flavio Leitner <fbl@redhat.com> - 2.6.1-0
- Updated to Open vSwitch 2.6.1

* Tue Nov 01 2016 Aaron Conole <aconole@redhat.com> - 2.6.0-0
- Update to Open vSwitch 2.6.0
- Enable OVN

* Wed Aug 24 2016 Dan Horák <dan[at]danny.cz> - 2.5.0-4
- don't run the test-suite for big endian arches

* Tue Jul 19 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.5.0-3
- https://fedoraproject.org/wiki/Changes/Automatic_Provides_for_Python_RPM_Packages

* Tue Mar 15 2016 Panu Matilainen <pmatilai@redhat.com> - 2.5.0-2
- Remove unpackaged files instead of excluding (#1281913)

* Wed Mar 02 2016 Panu Matilainen <pmatilai@redhat.com> - 2.5.0-1
- Update to 2.5.0 (#1312617)

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 2.4.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Mon Aug 24 2015 Flavio Leitner - 2.4.0-1
- updated to 2.4.0 (#1256171)

* Thu Jun 18 2015 Flavio Leitner - 2.3.2-1
- updated to 2.3.2 (#1233442)
- fixed to own /var/run/openvswitch directory (#1200887)

* Thu Jun 18 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.3.1-4.git20150327
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Fri Mar 27 2015 Flavio Leitner - 2.3.1-3.git20150327
- updated to 2.3.1-git4750c96
- commented out kernel requires
- added requires to procps-ng (testsuite #84)

* Wed Jan 14 2015 Flavio Leitner - 2.3.1-2.git20150113
- updated to 2.3.1-git3282e51

* Fri Dec 05 2014 Flavio Leitner - 2.3.1-1
- updated to 2.3.1

* Fri Nov 07 2014 Flavio Leitner - 2.3.0-3.git20141107
- updated to 2.3.0-git39ebb203

* Thu Oct 23 2014 Flavio Leitner - 2.3.0-2
- fixed to own conf.db and system-id.conf in /etc/openvswitch.
  (#1132707)

* Tue Aug 19 2014 Flavio Leitner - 2.3.0-1
- updated to 2.3.0

* Sun Aug 17 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.1.2-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Thu Jun 12 2014 Flavio Leitner - 2.1.2-4
- moved README.RHEL to be in the standard doc dir.
- added FAQ and NEWS files to the doc list.
- excluded PPC arch

* Thu Jun 12 2014 Flavio Leitner - 2.1.2-3
- removed ovsdbmonitor packaging

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.1.2-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Tue Mar 25 2014 Flavio Leitner - 2.1.2-1
- updated to 2.1.2

* Tue Mar 25 2014 Flavio Leitner - 2.1.0-1
- updated to 2.1.0
- obsoleted openvswitch-controller package
- requires kernel 3.15.0-0 or newer
  (kernel commit 4f647e0a3c37b8d5086214128614a136064110c3
   openvswitch: fix a possible deadlock and lockdep warning)
- ovs-lib: allow non-root users to check service status
  (upstream commit 691e47554dd03dd6492e00bab5bd6d215f5cbd4f)
- rhel: Add Patch Port support to initscripts
  (upstream commit e2bcc8ef49f5e51f48983b87ab1010f0f9ab1454)

* Mon Jan 27 2014 Flavio Leitner - 2.0.1-1
- updated to 2.0.1

* Mon Jan 27 2014 Flavio Leitner - 2.0.0-6
- create a -devel package
  (from Chris Wright <chrisw@redhat.com>)

* Wed Jan 15 2014 Flavio Leitner <fbl@redhat.com> - 2.0.0-5
- Enable DHCP support for internal ports
  (upstream commit 490db96efaf89c63656b192d5ca287b0908a6c77)

* Wed Jan 15 2014 Flavio Leitner <fbl@redhat.com> - 2.0.0-4
- disabled ovsdbmonitor packaging
  (upstream has removed the component)

* Wed Jan 15 2014 Flavio Leitner <fbl@redhat.com> - 2.0.0-3
- fedora package: fix systemd ordering and deps.
  (upstream commit b49c106ef00438b1c59876dad90d00e8d6e7b627)

* Wed Jan 15 2014 Flavio Leitner <fbl@redhat.com> - 2.0.0-2
- util: use gcc builtins to better check array sizes
  (upstream commit 878f1972909b33f27b32ad2ded208eb465b98a9b)

* Mon Oct 28 2013 Flavio Leitner <fbl@redhat.com> - 2.0.0-1
- updated to 2.0.0 (#1023184)

* Mon Oct 28 2013 Flavio Leitner <fbl@redhat.com> - 1.11.0-8
- applied upstream commit 7b75828bf5654c494a53fa57be90713c625085e2
  rhel: Option to create tunnel through ifcfg scripts.

* Mon Oct 28 2013 Flavio Leitner <fbl@redhat.com> - 1.11.0-7
- applied upstream commit 32aa46891af5e173144d672e15fec7c305f9a4f3
  rhel: Set STP of a bridge during bridge creation.

* Mon Oct 28 2013 Flavio Leitner <fbl@redhat.com> - 1.11.0-6
- applied upstream commit 5b56f96aaad4a55a26576e0610fb49bde448dabe
  rhel: Prevent duplicate ifup calls.

* Mon Oct 28 2013 Flavio Leitner <fbl@redhat.com> - 1.11.0-5
- applied upstream commit 79416011612541d103a1d396d888bb8c84eb1da4
  rhel: Return an exit value of 0 for ifup-ovs.

* Mon Oct 28 2013 Flavio Leitner <fbl@redhat.com> - 1.11.0-4
- applied upstream commit 2517bad92eec7e5625bc8b248db22fdeaa5fcde9
  Added RHEL ovs-ifup STP option handling

* Tue Oct 1 2013 Flavio Leitner <fbl@redhat.com> - 1.11.0-3
- don't use /var/lock/subsys with systemd (#1006412)

* Thu Sep 19 2013 Flavio Leitner <fbl@redhat.com> - 1.11.0-2
- ovsdbmonitor package is optional

* Thu Aug 29 2013 Thomas Graf <tgraf@redhat.com> - 1.11.0-1
- Update to 1.11.0

* Tue Aug 13 2013 Flavio Leitner <fbl@redhat.com> - 1.10.0-7
- Fixed openvswitch-nonetwork to start openvswitch.service (#996804)

* Sat Aug 03 2013 Petr Pisar <ppisar@redhat.com> - 1.10.0-6
- Perl 5.18 rebuild

* Tue Jul 23 2013 Thomas Graf <tgraf@redhat.com> - 1.10.0-5
- Typo

* Tue Jul 23 2013 Thomas Graf <tgraf@redhat.com> - 1.10.0-4
- Spec file fixes
- Maintain local copy of sysconfig.template

* Thu Jul 18 2013 Petr Pisar <ppisar@redhat.com> - 1.10.0-3
- Perl 5.18 rebuild

* Mon Jul 01 2013 Thomas Graf <tgraf@redhat.com> - 1.10.0-2
- Enable PIE (#955181)
- Provide native systemd unit files (#818754)

* Thu May 02 2013 Thomas Graf <tgraf@redhat.com> - 1.10.0-1
- Update to 1.10.0 (#958814)

* Thu Feb 28 2013 Thomas Graf <tgraf@redhat.com> - 1.9.0-1
- Update to 1.9.0 (#916537)

* Tue Feb 12 2013 Thomas Graf <tgraf@redhat.com> - 1.7.3-8
- Fix systemd service dependency loop (#818754)

* Fri Jan 25 2013 Thomas Graf <tgraf@redhat.com> - 1.7.3-7
- Auto-start openvswitch service on ifup/ifdown (#818754)
- Add OVSREQUIRES to allow defining OpenFlow interface dependencies

* Thu Jan 24 2013 Thomas Graf <tgraf@redhat.com> - 1.7.3-6
- Update to Open vSwitch 1.7.3

* Tue Nov 20 2012 Thomas Graf <tgraf@redhat.com> - 1.7.1-6
- Increase max fd limit to support 256 bridges (#873072)

* Thu Nov  1 2012 Thomas Graf <tgraf@redhat.com> - 1.7.1-5
- Don't create world writable pki/*/incomming directory (#845351)

* Thu Oct 25 2012 Thomas Graf <tgraf@redhat.com> - 1.7.1-4
- Don't add iptables accept rule for -p GRE as GRE tunneling is unsupported

* Tue Oct 16 2012 Thomas Graf <tgraf@redhat.com> - 1.7.1-3
- require systemd instead of systemd-units to use macro helpers (#850258)

* Tue Oct  9 2012 Thomas Graf <tgraf@redhat.com> - 1.7.1-2
- make ovs-vsctl timeout if daemon is not running (#858722)

* Mon Sep 10 2012 Thomas Graf <tgraf@redhat.com> - 1.7.1.-1
- Update to 1.7.1

* Fri Sep  7 2012 Thomas Graf <tgraf@redhat.com> - 1.7.0.-3
- add controller package containing ovs-controller

* Thu Aug 23 2012 Tomas Hozza <thozza@redhat.com> - 1.7.0-2
- fixed SPEC file so it comply with new systemd-rpm macros guidelines (#850258)

* Fri Aug 17 2012 Tomas Hozza <thozza@redhat.com> - 1.7.0-1
- Update to 1.7.0
- Fixed openvswitch-configure-ovskmod-var-autoconfd.patch because
  openvswitch kernel module name changed in 1.7.0
- Removed Source8: ovsdbmonitor-move-to-its-own-data-directory.patch
- Patches merged:
  - ovsdbmonitor-move-to-its-own-data-directory-automaked.patch
  - openvswitch-rhel-initscripts-resync.patch

* Fri Jul 20 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.4.0-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Thu Mar 15 2012 Chris Wright <chrisw@redhat.com> - 1.4.0-5
- fix ovs network initscripts DHCP address acquisition (#803843)

* Tue Mar  6 2012 Chris Wright <chrisw@redhat.com> - 1.4.0-4
- make BuildRequires openssl explicit (needed on f18/rawhide now)

* Tue Mar  6 2012 Chris Wright <chrisw@redhat.com> - 1.4.0-3
- use glob to catch compressed manpages

* Thu Mar  1 2012 Chris Wright <chrisw@redhat.com> - 1.4.0-2
- Update License comment, use consitent macros as per review comments bz799171

* Wed Feb 29 2012 Chris Wright <chrisw@redhat.com> - 1.4.0-1
- Initial package for Fedora
