Name: kexec-tools
Version: 2.0.21
Release: 1%{?_tis_dist}.%{tis_patch_ver}
License: GPLv2
Group: Applications/System
Summary: The kexec/kdump userspace component.
Source0: http://kernel.org/pub/linux/utils/kernel/kexec/%{name}-%{version}.tar.xz
Source1: kdumpctl
Source2: kdump.sysconfig
Source3: kdump.sysconfig.x86_64
Source7: mkdumprd
Source8: kdump.conf
Source9: makedumpfile-1.6.9.tar.gz
Source10: kexec-kdump-howto.txt
Source12: mkdumprd.8
Source14: 98-kexec.rules
Source15: kdump.conf.5
Source16: kdump.service
Source19: eppic_050615.tar.gz
Source20: kdump-lib.sh
Source21: kdump-in-cluster-environment.txt
Source22: supported-kdump-targets.txt
Source23: kdump-dep-generator.sh
Source24: kdump-lib-initramfs.sh
Source25: kdump-anaconda-addon-003-29-g4c517c5.tar.gz
Source28: kdumpctl.8

#######################################
# These are sources for mkdumpramfs
# Which is currently in development
#######################################
Source100: dracut-kdump.sh
Source101: dracut-module-setup.sh
Source102: dracut-monitor_dd_progress
Source103: dracut-kdump-error-handler.sh
Source104: dracut-kdump-emergency.service
Source105: dracut-kdump-error-handler.service
Source106: dracut-kdump-capture.service
Source107: dracut-kdump-emergency.target

Requires(post): systemd-units
Requires(preun): systemd-units
Requires(postun): systemd-units
Requires(pre): coreutils sed zlib 
Requires: dracut >= 033-552
Requires: dracut-network >= 033-552
Requires: ethtool
BuildRequires: zlib-devel zlib zlib-static elfutils-devel-static glib2-devel bzip2-devel ncurses-devel bison flex lzo-devel snappy-devel
BuildRequires: pkgconfig intltool gettext 
BuildRequires: systemd-units
%ifarch %{ix86} x86_64
Obsoletes: diskdumputils netdump
%endif


#START INSERT

#
# Patches 0 through 100 are meant for x86 kexec-tools enablement
#

#
# Patches 101 through 200 are meant for x86_64 kexec-tools enablement
#

#
# Patches 601 through 700 are meant for arm64 kexec-tools enablement
#
#
# Patches 701 onward are generic patches
#

#
# Patch 701 through 800 are meant for kdump anaconda addon
#

%description
kexec-tools provides /sbin/kexec binary that facilitates a new
kernel to boot using the kernel's kexec feature either on a
normal or a panic reboot. This package contains the /sbin/kexec
binary and ancillary utilities that together form the userspace
component of the kernel's kexec feature.

%ifarch %{ix86} x86_64
%package eppic
Requires: %{name} = %{version}-%{release}
Summary: Additional eppic_makedumpfile.so shared object
Group: Applications/System

%description eppic
The eppic_makedumpfile.so shared object is loaded by the
"makedumpfile --eppic" option, and is used to erase sensitive
or confidential kernel data from a dumpfile.
%endif

%package anaconda-addon
Summary:        Kdump configration anaconda addon
Requires:       anaconda >= 19.31.85
%description anaconda-addon
Kdump anaconda addon

%prep
%setup -q 

mkdir -p -m755 kcp
tar -z -x -v -f %{SOURCE9}
tar -z -x -v -f %{SOURCE19}
tar -z -x -v -f %{SOURCE25}




%build
%configure \
    --sbindir=/sbin
rm -f kexec-tools.spec.in
# setup the docs
cp %{SOURCE10} .
cp %{SOURCE21} .
cp %{SOURCE22} . 

make
%ifarch %{ix86} x86_64
make -C eppic/libeppic
make -C makedumpfile-1.6.9 LINKTYPE=dynamic USELZO=on USESNAPPY=on
make -C makedumpfile-1.6.9 LDFLAGS="-I../eppic/libeppic -L../eppic/libeppic" eppic_makedumpfile.so
%endif
make -C kdump-anaconda-addon/po

%install
mkdir -p -m755 $RPM_BUILD_ROOT/sbin
mkdir -p -m755 $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig
mkdir -p -m755 $RPM_BUILD_ROOT%{_localstatedir}/crash
mkdir -p -m755 $RPM_BUILD_ROOT%{_mandir}/man8/
mkdir -p -m755 $RPM_BUILD_ROOT%{_mandir}/man5/
mkdir -p -m755 $RPM_BUILD_ROOT%{_docdir}
mkdir -p -m755 $RPM_BUILD_ROOT%{_datadir}/kdump
mkdir -p -m755 $RPM_BUILD_ROOT%{_udevrulesdir}
mkdir -p $RPM_BUILD_ROOT%{_unitdir}
mkdir -p -m755 $RPM_BUILD_ROOT%{_bindir}
mkdir -p -m755 $RPM_BUILD_ROOT%{_libdir}
mkdir -p -m755 $RPM_BUILD_ROOT%{_prefix}/lib/kdump
install -m 755 %{SOURCE1} $RPM_BUILD_ROOT%{_bindir}/kdumpctl

install -m 755 build/sbin/kexec $RPM_BUILD_ROOT/sbin/kexec
install -m 755 build/sbin/vmcore-dmesg $RPM_BUILD_ROOT/sbin/vmcore-dmesg
install -m 644 build/man/man8/kexec.8  $RPM_BUILD_ROOT%{_mandir}/man8/
install -m 644 build/man/man8/vmcore-dmesg.8  $RPM_BUILD_ROOT%{_mandir}/man8/

SYSCONFIG=$RPM_SOURCE_DIR/kdump.sysconfig.%{_target_cpu}
[ -f $SYSCONFIG ] || SYSCONFIG=$RPM_SOURCE_DIR/kdump.sysconfig.%{_arch}
[ -f $SYSCONFIG ] || SYSCONFIG=$RPM_SOURCE_DIR/kdump.sysconfig
install -m 644 $SYSCONFIG $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/kdump

install -m 755 %{SOURCE7} $RPM_BUILD_ROOT/sbin/mkdumprd
install -m 644 %{SOURCE8} $RPM_BUILD_ROOT%{_sysconfdir}/kdump.conf
install -m 644 kexec/kexec.8 $RPM_BUILD_ROOT%{_mandir}/man8/kexec.8
install -m 644 %{SOURCE12} $RPM_BUILD_ROOT%{_mandir}/man8/mkdumprd.8
install -m 644 %{SOURCE28} $RPM_BUILD_ROOT%{_mandir}/man8/kdumpctl.8
install -m 755 %{SOURCE20} $RPM_BUILD_ROOT%{_prefix}/lib/kdump/kdump-lib.sh
install -m 755 %{SOURCE24} $RPM_BUILD_ROOT%{_prefix}/lib/kdump/kdump-lib-initramfs.sh
install -m 644 %{SOURCE14} $RPM_BUILD_ROOT%{_udevrulesdir}/98-kexec.rules
install -m 644 %{SOURCE15} $RPM_BUILD_ROOT%{_mandir}/man5/kdump.conf.5
install -m 644 %{SOURCE16} $RPM_BUILD_ROOT%{_unitdir}/kdump.service
install -m 755 -D %{SOURCE23} $RPM_BUILD_ROOT%{_prefix}/lib/systemd/system-generators/kdump-dep-generator.sh

%ifarch %{ix86} x86_64
install -m 755 makedumpfile-1.6.9/makedumpfile $RPM_BUILD_ROOT/sbin/makedumpfile
install -m 644 makedumpfile-1.6.9/makedumpfile.8.gz $RPM_BUILD_ROOT/%{_mandir}/man8/makedumpfile.8.gz
install -m 644 makedumpfile-1.6.9/makedumpfile.conf.5.gz $RPM_BUILD_ROOT/%{_mandir}/man5/makedumpfile.conf.5.gz
install -m 644 makedumpfile-1.6.9/makedumpfile.conf $RPM_BUILD_ROOT/%{_sysconfdir}/makedumpfile.conf.sample
install -m 755 makedumpfile-1.6.9/eppic_makedumpfile.so $RPM_BUILD_ROOT/%{_libdir}/eppic_makedumpfile.so
mkdir -p $RPM_BUILD_ROOT/usr/share/makedumpfile/eppic_scripts/
install -m 644 makedumpfile-1.6.9/eppic_scripts/* $RPM_BUILD_ROOT/usr/share/makedumpfile/eppic_scripts/
%endif
make -C kdump-anaconda-addon install DESTDIR=$RPM_BUILD_ROOT
%find_lang kdump-anaconda-addon

%define remove_dracut_prefix() %(echo -n %1|sed 's/.*dracut-//g')

# deal with dracut modules
mkdir -p -m755 $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase
cp %{SOURCE100} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE100}}
cp %{SOURCE101} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE101}}
cp %{SOURCE102} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE102}}
cp %{SOURCE103} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE103}}
cp %{SOURCE104} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE104}}
cp %{SOURCE105} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE105}}
cp %{SOURCE106} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE106}}
cp %{SOURCE107} $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE107}}
chmod 755 $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE100}}
chmod 755 $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/99kdumpbase/%{remove_dracut_prefix %{SOURCE101}}


%define dracutlibdir %{_prefix}/lib/dracut
#and move the custom dracut modules to the dracut directory
mkdir -p $RPM_BUILD_ROOT/%{dracutlibdir}/modules.d/
mv $RPM_BUILD_ROOT/etc/kdump-adv-conf/kdump_dracut_modules/* $RPM_BUILD_ROOT/%{dracutlibdir}/modules.d/

%post
# Initial installation
%systemd_post kdump.service

touch /etc/kdump.conf
# This portion of the script is temporary.  Its only here
# to fix up broken boxes that require special settings 
# in /etc/sysconfig/kdump.  It will be removed when 
# These systems are fixed.

if [ -d /proc/bus/mckinley ]
then
	# This is for HP zx1 machines
	# They require machvec=dig on the kernel command line
	sed -e's/\(^KDUMP_COMMANDLINE_APPEND.*\)\("$\)/\1 machvec=dig"/' \
	/etc/sysconfig/kdump > /etc/sysconfig/kdump.new
	mv /etc/sysconfig/kdump.new /etc/sysconfig/kdump
elif [ -d /proc/sgi_sn ]
then
	# This is for SGI SN boxes
	# They require the --noio option to kexec 
	# since they don't support legacy io
	sed -e's/\(^KEXEC_ARGS.*\)\("$\)/\1 --noio"/' \
	/etc/sysconfig/kdump > /etc/sysconfig/kdump.new
	mv /etc/sysconfig/kdump.new /etc/sysconfig/kdump
fi


%postun
%systemd_postun_with_restart kdump.service

%preun
# Package removal, not upgrade
%systemd_preun kdump.service

%triggerun -- kexec-tools < 2.0.2-3
# Save the current service runlevel info
# User must manually run systemd-sysv-convert --apply kdump
# to migrate them to systemd targets
/usr/bin/systemd-sysv-convert --save kdump >/dev/null 2>&1 ||:

# Run these because the SysV package being removed won't do them
/sbin/chkconfig --del kdump >/dev/null 2>&1 || :
/bin/systemctl try-restart kdump.service >/dev/null 2>&1 || :


%triggerin -- kernel-kdump
touch %{_sysconfdir}/kdump.conf


%triggerpostun -- kernel kernel-xen kernel-debug kernel-PAE kernel-kdump
# List out the initrds here, strip out version nubmers
# and search for corresponding kernel installs, if a kernel
# is not found, remove the corresponding kdump initrd

#start by getting a list of all the kdump initrds
MY_ARCH=`uname -m`
IMGDIR=/boot

for i in `ls $IMGDIR/initramfs*kdump.img 2>/dev/null`
do
	KDVER=`echo $i | sed -e's/^.*initramfs-//' -e's/kdump.*$//'`
	if [ ! -e $IMGDIR/vmlinuz-$KDVER ]
	then
		# We have found an initrd with no corresponding kernel
		# so we should be able to remove it
		rm -f $i
	fi
done

%files
/sbin/kexec
/sbin/vmcore-dmesg
%ifarch %{ix86} x86_64
/sbin/makedumpfile
%endif
/sbin/mkdumprd
%{_bindir}/*
%{_datadir}/kdump
%{_prefix}/lib/kdump
%ifarch %{ix86} x86_64
%{_sysconfdir}/makedumpfile.conf.sample
%endif
%config(noreplace,missingok) %{_sysconfdir}/sysconfig/kdump
%config(noreplace,missingok) %verify(not mtime) %{_sysconfdir}/kdump.conf
%config %{_udevrulesdir}
%{dracutlibdir}/modules.d/*
%dir %{_localstatedir}/crash
%{_mandir}/man8/kdumpctl.8.gz
%{_mandir}/man8/kexec.8.gz
%ifarch %{ix86} x86_64
%{_mandir}/man8/makedumpfile.8.gz
%endif
%{_mandir}/man8/mkdumprd.8.gz
%{_mandir}/man8/vmcore-dmesg.8.gz
%{_mandir}/man5/*
%{_unitdir}/kdump.service
%{_prefix}/lib/systemd/system-generators/kdump-dep-generator.sh
%doc News
%doc COPYING
%doc TODO
%doc kexec-kdump-howto.txt
%doc kdump-in-cluster-environment.txt
%doc supported-kdump-targets.txt

%ifarch %{ix86} x86_64
%files eppic
%{_libdir}/eppic_makedumpfile.so
/usr/share/makedumpfile/eppic_scripts/
%endif

%files anaconda-addon -f kdump-anaconda-addon.lang
%{_datadir}/anaconda/addons/com_redhat_kdump
%{_datadir}/icons/hicolor/scalable/apps/kdump.svg
%doc

%changelog
* Fri Jul 30 2021 M. Vefa Bicakci <vefa.bicakci@windriver.com> 2.0.21-1.tis.1
- Adapt to kexec-tools 2.0.21 for v5.10 kernel, while attempting to keep
  compatibility with CentOS 7.
- Use makedumpfile 1.6.9 for compatibility with the v5.10 kernel.
- Remove aarch64, PowerPC, ia64 and s390-related spec file sections.
- Trim the spec file changelog.

* Thu Aug 30 2018 Pingfan Liu <piliu@redhat.com> 2.0.15-21
- kexec/ppc64: add support to parse ibm, dynamic-memory-v2 
