%global SLOF_gittagdate 20160223
%global SLOF_gittagcommit dbbfda4

%global have_usbredir 1
%global have_spice    1
%global have_fdt      1
%global have_gluster  0
%global have_kvm_setup 0
%global have_seccomp 1
%global have_memlock_limits 0

%ifnarch %{ix86} x86_64 aarch64
    %global have_seccomp 0
%endif

%ifnarch %{ix86} x86_64
    %global have_usbredir 0
%endif

%ifnarch s390 s390x
    %global have_librdma 1
    %global have_tcmalloc 1
%else
    %global have_librdma 0
    %global have_tcmalloc 0
%endif

%ifarch %{ix86}
    %global kvm_target    i386
%endif
%ifarch x86_64
    %global kvm_target    x86_64
%else
    %global have_spice   0
    %global have_gluster 0
%endif
%ifarch %{power64}
    %global kvm_target    ppc64
    %global have_fdt     1
    %global have_kvm_setup 1
    %global have_memlock_limits 1
%endif
%ifarch s390x s390
    %global kvm_target    s390x
%endif
%ifarch ppc
    %global kvm_target    ppc
    %global have_fdt     1
%endif
%ifarch aarch64
    %global kvm_target    aarch64
    %global have_fdt     1
%endif

#Versions of various parts:

%define pkgname qemu-kvm
%define rhel_suffix -rhel
%define rhev_suffix -rhev

# Setup for RHEL/RHEV package handling
# We need to define tree suffixes:
# - pkgsuffix:             used for package name
# - extra_provides_suffix: used for dependency checking of other packages
# - conflicts_suffix:      used to prevent installation of both RHEL and RHEV

%global pkgsuffix -ev
%global extra_provides_suffix %{nil}
%global rhev_provide_suffix %{rhev_suffix}
%global conflicts_suffix %{rhel_suffix}
%global obsoletes_version 15:0-0

# Macro to properly setup RHEL/RHEV conflict handling
%define rhel_rhev_conflicts()                                         \
Conflicts: %1%{conflicts_suffix}                                      \
Provides: %1%{extra_provides_suffix} = %{epoch}:%{version}-%{release} \
    %if 0%{?rhev_provide_suffix:1}                                     \
Provides: %1%{rhev_provide_suffix} = %{epoch}:%{version}-%{release}   \
Obsoletes: %1%{rhev_provide_suffix} < %{epoch}:%{version}-%{release}   \
    %endif                                                            \
Obsoletes: %1 < %{obsoletes_version}

Summary: QEMU is a FAST! processor emulator
Name:    %{pkgname}%{?pkgsuffix}
Version: 3.0.0
Release: 0%{?_tis_dist}.%{tis_patch_ver}
# Epoch because we pushed a qemu-1.0 package. AIUI this can't ever be dropped
Epoch: 10
License: GPLv2+ and LGPLv2+ and BSD
Group: Development/Tools
URL: http://www.qemu.org/
# RHEV will build Qemu only on x86_64:
ExclusiveArch: x86_64 %{power64} aarch64
%ifarch %{ix86} x86_64
Requires: seabios-bin >= 1.7.5-1
Requires: sgabios-bin
%endif
%ifnarch aarch64
Requires: seavgabios-bin >= 1.9.1-4
Requires: ipxe-roms-qemu >= 20160127-4
%endif
%ifarch %{power64}
Requires: SLOF >= %{SLOF_gittagdate}-1.git%{SLOF_gittagcommit}
%endif
Requires: %{pkgname}-common%{?pkgsuffix} = %{epoch}:%{version}-%{release}
%if %{have_seccomp}
Requires: libseccomp >= 1.0.0
%endif
# For compressed guest memory dumps
Requires: lzo snappy
%if %{have_gluster}
Requires: glusterfs-api >= 3.6.0
%endif
%if %{have_kvm_setup}
Requires(post): systemd-units
    %ifarch %{power64}
Requires: powerpc-utils
    %endif
%endif
Requires: libusbx >= 1.0.19
%if %{have_usbredir}
Requires: usbredir >= 0.7.1
%endif

# OOM killer breaks builds with parallel make on s390(x)
%ifarch s390 s390x
    %define _smp_mflags %{nil}
%endif

Source0: qemu-kvm-ev-%{version}.tar.gz

Source1: qemu.binfmt
# Creates /dev/kvm
Source3: 80-kvm.rules
# KSM control scripts
# Source4: ksm.service
# Source5: ksm.sysconfig
# Source6: ksmctl.c
# Source7: ksmtuned.service
# Source8: ksmtuned
# Source9: ksmtuned.conf
Source10: qemu-guest-agent.service
Source11: 99-qemu-guest-agent.rules
Source12: bridge.conf
Source13: qemu-ga.sysconfig
Source14: rhel6-virtio.rom
Source15: rhel6-pcnet.rom
Source16: rhel6-rtl8139.rom
Source17: rhel6-ne2k_pci.rom
Source18: bios-256k.bin
Source19: README.rhel6-gpxe-source
Source20: rhel6-e1000.rom
Source21: kvm-setup
Source22: kvm-setup.service
Source23: 85-kvm.preset
Source24: build_configure.sh
Source25: kvm-unit-tests.git-4ea7633.tar.bz2
Source26: vhost.conf
Source27: kvm.conf
Source28: 95-kvm-memlock.conf
Source29: keycodemapdb-16e5b07.tar.gz

#WRS
Source127: qemu_clean
Source128: qemu_clean.service
Source129: qemu-system-x86.conf


BuildRequires: zlib-devel
BuildRequires: SDL-devel
BuildRequires: which
BuildRequires: texi2html
BuildRequires: gnutls-devel
BuildRequires: cyrus-sasl-devel
BuildRequires: libtool
BuildRequires: libaio-devel
BuildRequires: rsync
BuildRequires: python
BuildRequires: pciutils-devel
BuildRequires: pulseaudio-libs-devel
BuildRequires: libiscsi-devel
BuildRequires: ncurses-devel
BuildRequires: libattr-devel
BuildRequires: libusbx-devel >= 1.0.19
BuildRequires: systemd-devel
%if %{have_usbredir}
BuildRequires: usbredir-devel >= 0.7.1
%endif
BuildRequires: texinfo
%if %{have_spice}
BuildRequires: spice-protocol >= 0.12.2
BuildRequires: spice-server-devel >= 0.12.0
BuildRequires: libcacard-devel
# For smartcard NSS support
BuildRequires: nss-devel
%endif
%if %{have_seccomp}
BuildRequires: libseccomp-devel >= 1.0.0
%endif
# For network block driver
BuildRequires: libcurl-devel
BuildRequires: libssh2-devel
%ifarch x86_64
BuildRequires: librados2-devel
BuildRequires: librbd1-devel
%endif
%if %{have_gluster}
# For gluster block driver
BuildRequires: glusterfs-api-devel >= 3.6.0
BuildRequires: glusterfs-devel
%endif
# We need both because the 'stap' binary is probed for by configure
BuildRequires: systemtap
BuildRequires: systemtap-sdt-devel
# For XFS discard support in raw-posix.c
# For VNC JPEG support
BuildRequires: libjpeg-devel
# For VNC PNG support
BuildRequires: libpng-devel
# For uuid generation
BuildRequires: libuuid-devel
# For BlueZ device support
BuildRequires: bluez-libs-devel
# For Braille device support
BuildRequires: brlapi-devel
# For test suite
BuildRequires: check-devel
# For virtfs
BuildRequires: libcap-devel
# Hard requirement for version >= 1.3
BuildRequires: pixman-devel
# Documentation requirement
BuildRequires: perl-podlators
BuildRequires: texinfo
# For rdma
%if 0%{?have_librdma}
BuildRequires: librdmacm-devel
%endif
%if 0%{?have_tcmalloc}
BuildRequires: gperftools-devel
%endif
%if %{have_fdt}
BuildRequires: libfdt-devel >= 1.4.2
%endif
# iasl and cpp for acpi generation (not a hard requirement as we can use
# pre-compiled files, but it's better to use this)
%ifarch %{ix86} x86_64
BuildRequires: iasl
BuildRequires: cpp
%endif
# For compressed guest memory dumps
BuildRequires: lzo-devel snappy-devel
# For NUMA memory binding
BuildRequires: numactl-devel
BuildRequires: libgcrypt-devel

# For kvm-unit-tests
%ifarch x86_64
BuildRequires: binutils
BuildRequires: kernel-devel
%endif

# WRS: build_configure.sh enables libcap-ng
BuildRequires: libcap-ng-devel

Requires: qemu-img%{?pkgsuffix} = %{epoch}:%{version}-%{release}

# RHEV-specific changes:
# We provide special suffix for qemu-kvm so the conflit is easy
# In addition, RHEV version should obsolete all RHEL version in case both
# RHEL and RHEV channels are used
%rhel_rhev_conflicts qemu-kvm


%define qemudocdir %{_docdir}/%{pkgname}

%description
qemu-kvm is an open source virtualizer that provides hardware emulation for
the KVM hypervisor. qemu-kvm acts as a virtual machine monitor together with
the KVM kernel modules, and emulates the hardware for a full system such as
a PC and its assocated peripherals.

As qemu-kvm requires no host kernel patches to run, it is safe and easy to use.

%package -n qemu-img%{?pkgsuffix}
Summary: QEMU command line tool for manipulating disk images
Group: Development/Tools

%rhel_rhev_conflicts qemu-img

%description -n qemu-img%{?pkgsuffix}
This package provides a command line tool for manipulating disk images.

%package -n qemu-kvm-common%{?pkgsuffix}
Summary: QEMU common files needed by all QEMU targets
Group: Development/Tools
Requires(post): /usr/bin/getent
Requires(post): /usr/sbin/groupadd
Requires(post): /usr/sbin/useradd
Requires(post): systemd-units
Requires(preun): systemd-units
Requires(postun): systemd-units

%rhel_rhev_conflicts qemu-kvm-common

%description -n qemu-kvm-common%{?pkgsuffix}
qemu-kvm is an open source virtualizer that provides hardware emulation for
the KVM hypervisor.

This package provides documentation and auxiliary programs used with qemu-kvm.

%package -n qemu-kvm-tools%{?pkgsuffix}
Summary: KVM debugging and diagnostics tools
Group: Development/Tools

%rhel_rhev_conflicts qemu-kvm-tools

%description -n qemu-kvm-tools%{?pkgsuffix}
This package contains some diagnostics and debugging tools for KVM,
such as kvm_stat.

%if 0
%package -n libcacard%{?pkgsuffix}
Summary:        Common Access Card (CAC) Emulation
Group:          Development/Libraries

%rhel_rhev_conflicts libcacard

%description -n libcacard%{?pkgsuffix}
Common Access Card (CAC) emulation library.

%package -n libcacard-tools%{?pkgsuffix}
Summary:        CAC Emulation tools
Group:          Development/Libraries
Requires:       libcacard%{?pkgsuffix} = %{epoch}:%{version}-%{release}
# older qemu-img has vscclient which is now in libcacard-tools
Requires:       qemu-img%{?pkgsuffix} >= 3:1.3.0-5

%rhel_rhev_conflicts libcacard-tools

%description -n libcacard-tools%{?pkgsuffix}
CAC emulation tools.

%package -n libcacard-devel%{?pkgsuffix}
Summary:        CAC Emulation devel
Group:          Development/Libraries
Requires:       libcacard%{?pkgsuffix} = %{epoch}:%{version}-%{release}

%rhel_rhev_conflicts libcacard-devel

%description -n libcacard-devel%{?pkgsuffix}
CAC emulation development files.
%endif

%prep
%setup -q -n qemu-kvm-ev-%{version}

# Copy bios files to allow 'make check' pass
cp %{SOURCE14} pc-bios
cp %{SOURCE15} pc-bios
cp %{SOURCE16} pc-bios
cp %{SOURCE17} pc-bios
cp %{SOURCE18} pc-bios
cp %{SOURCE20} pc-bios

# if patch fuzzy patch applying will be forbidden
%define with_fuzzy_patches 0
%if %{with_fuzzy_patches}
    patch_command='patch -p1 -s'
%else
    patch_command='patch -p1 -F1 -s'
%endif

ApplyPatch()
{
  local patch=$1
  shift
  if [ ! -f $RPM_SOURCE_DIR/$patch ]; then
    exit 1
  fi
  case "$patch" in
  *.bz2) bunzip2 < "$RPM_SOURCE_DIR/$patch" | $patch_command ${1+"$@"} ;;
  *.gz) gunzip < "$RPM_SOURCE_DIR/$patch" | $patch_command ${1+"$@"} ;;
  *) $patch_command ${1+"$@"} < "$RPM_SOURCE_DIR/$patch" ;;
  esac
}

# don't apply patch if it's empty or does not exist
ApplyOptionalPatch()
{
  local patch=$1
  shift
  if [ ! -f $RPM_SOURCE_DIR/$patch ]; then
    return 0
  fi
  local C=$(wc -l $RPM_SOURCE_DIR/$patch | awk '{print $1}')
  if [ "$C" -gt 9 ]; then
    ApplyPatch $patch ${1+"$@"}
  fi
}


ApplyOptionalPatch qemu-kvm-test.patch

# for tscdeadline_latency.flat
%ifarch x86_64
  tar -xf %{SOURCE25}
%endif

%build
buildarch="%{kvm_target}-softmmu"

# --build-id option is used for giving info to the debug packages.
extraldflags="-Wl,--build-id";
buildldflags="VL_LDFLAGS=-Wl,--build-id"

# QEMU already knows how to set _FORTIFY_SOURCE
%global optflags %(echo %{optflags} | sed 's/-Wp,-D_FORTIFY_SOURCE=2//')

%ifarch s390
    # drop -g flag to prevent memory exhaustion by linker
    %global optflags %(echo %{optflags} | sed 's/-g//')
    sed -i.debug 's/"-g $CFLAGS"/"$CFLAGS"/g' configure
%endif

tar xzf %{SOURCE29} -C ui

cp %{SOURCE24} build_configure.sh

./build_configure.sh  \
  "%{_prefix}" \
  "%{_libdir}" \
  "%{_sysconfdir}" \
  "%{_localstatedir}" \
  "%{_libexecdir}" \
  "%{pkgname}" \
  "%{kvm_target}" \
  "%{name}-%{version}-%{release}" \
  "%{optflags}" \
%if 0%{have_fdt}
  enable \
%else
  disable \
%endif
%if 0%{have_gluster}
  enable \
%else
  disable \
%endif
  disable \
  enable \
%ifarch x86_64
  enable \
%else
  disable \
%endif
  enable \
%if 0%{have_seccomp}
  enable \
%else
  disable \
%endif
%if 0%{have_spice}
  enable \
%else
  disable \
%endif
%if 0%{have_usbredir}
  enable \
%else
  disable \
%endif
%if 0%{have_tcmalloc}
  enable \
%else
  disable \
%endif
  --target-list="$buildarch"

echo "config-host.mak contents:"
echo "==="
cat config-host.mak
echo "==="

make V=1 %{?_smp_mflags} $buildldflags

# WRS: Disable - we are not using traces
# Setup back compat qemu-kvm binary
# ./scripts/tracetool.py --backend dtrace --format stap \
#   --binary %{_libexecdir}/qemu-kvm --target-name %{kvm_target} \
#   --target-type system --probe-prefix \
#   qemu.kvm < ./trace-events > qemu-kvm.stp

# ./scripts/tracetool.py --backend dtrace --format simpletrace-stap \
#   --binary %{_libexecdir}/qemu-kvm --target-name %{kvm_target} \
#   --target-type system --probe-prefix \
#   qemu.kvm < ./trace-events > qemu-kvm-simpletrace.stp

cp -a %{kvm_target}-softmmu/qemu-system-%{kvm_target} qemu-kvm


# gcc %{SOURCE6} -O2 -g -o ksmctl

# build tscdeadline_latency.flat
%ifarch x86_64
  (cd  kvm-unit-tests && ./configure)
  make -C kvm-unit-tests
%endif

%install
%define _udevdir %(pkg-config --variable=udevdir udev)/rules.d

# install -D -p -m 0644 %{SOURCE4} $RPM_BUILD_ROOT%{_unitdir}/ksm.service
# install -D -p -m 0644 %{SOURCE5} $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/ksm
# install -D -p -m 0755 ksmctl $RPM_BUILD_ROOT%{_libexecdir}/ksmctl

# install -D -p -m 0644 %{SOURCE7} $RPM_BUILD_ROOT%{_unitdir}/ksmtuned.service
# install -D -p -m 0755 %{SOURCE8} $RPM_BUILD_ROOT%{_sbindir}/ksmtuned
# install -D -p -m 0644 %{SOURCE9} $RPM_BUILD_ROOT%{_sysconfdir}/ksmtuned.conf
install -D -p -m 0644 %{SOURCE26} $RPM_BUILD_ROOT%{_sysconfdir}/modprobe.d/vhost.conf
install -D -p -m 0644 %{SOURCE129} $RPM_BUILD_ROOT%{_sysconfdir}/modprobe.d/qemu-system-x86.conf

mkdir -p $RPM_BUILD_ROOT%{_bindir}/
mkdir -p $RPM_BUILD_ROOT%{_udevdir}

install -m 0644 %{SOURCE3} $RPM_BUILD_ROOT%{_udevdir}

mkdir -p $RPM_BUILD_ROOT%{_datadir}/%{pkgname}
install -m 0644 scripts/dump-guest-memory.py \
                $RPM_BUILD_ROOT%{_datadir}/%{pkgname}
%ifarch x86_64
    install -m 0644 kvm-unit-tests/x86/tscdeadline_latency.flat \
                    $RPM_BUILD_ROOT%{_datadir}/%{pkgname}
%endif

make DESTDIR=$RPM_BUILD_ROOT \
    sharedir="%{_datadir}/%{pkgname}" \
    datadir="%{_datadir}/%{pkgname}" \
    install

mkdir -p $RPM_BUILD_ROOT%{_datadir}/systemtap/tapset

# Install compatibility roms
install %{SOURCE14} $RPM_BUILD_ROOT%{_datadir}/%{pkgname}/
install %{SOURCE15} $RPM_BUILD_ROOT%{_datadir}/%{pkgname}/
install %{SOURCE16} $RPM_BUILD_ROOT%{_datadir}/%{pkgname}/
install %{SOURCE17} $RPM_BUILD_ROOT%{_datadir}/%{pkgname}/
install %{SOURCE20} $RPM_BUILD_ROOT%{_datadir}/%{pkgname}/

install -m 0755 qemu-kvm $RPM_BUILD_ROOT%{_libexecdir}/
# WRS: Disable traces
# install -m 0644 qemu-kvm.stp $RPM_BUILD_ROOT%{_datadir}/systemtap/tapset/
# install -m 0644 qemu-kvm-simpletrace.stp $RPM_BUILD_ROOT%{_datadir}/systemtap/tapset/

# WRS: Add kvm softlink
ln -sf %{_libexecdir}/qemu-kvm $RPM_BUILD_ROOT/usr/bin/kvm

rm $RPM_BUILD_ROOT%{_bindir}/qemu-system-%{kvm_target}
# WRS: Disable traces
# rm $RPM_BUILD_ROOT%{_datadir}/systemtap/tapset/qemu-system-%{kvm_target}.stp
# rm $RPM_BUILD_ROOT%{_datadir}/systemtap/tapset/qemu-system-%{kvm_target}-simpletrace.stp

# Install simpletrace
# install -m 0755 scripts/simpletrace.py $RPM_BUILD_ROOT%{_datadir}/%{pkgname}/simpletrace.py
# mkdir -p $RPM_BUILD_ROOT%{_datadir}/%{pkgname}/tracetool
# install -m 0644 -t $RPM_BUILD_ROOT%{_datadir}/%{pkgname}/tracetool scripts/tracetool/*.py
# mkdir -p $RPM_BUILD_ROOT%{_datadir}/%{pkgname}/tracetool/backend
# install -m 0644 -t $RPM_BUILD_ROOT%{_datadir}/%{pkgname}/tracetool/backend scripts/tracetool/backend/*.py
# mkdir -p $RPM_BUILD_ROOT%{_datadir}/%{pkgname}/tracetool/format
# install -m 0644 -t $RPM_BUILD_ROOT%{_datadir}/%{pkgname}/tracetool/format scripts/tracetool/format/*.py

mkdir -p $RPM_BUILD_ROOT%{qemudocdir}
install -p -m 0644 -t ${RPM_BUILD_ROOT}%{qemudocdir} Changelog README README.systemtap COPYING COPYING.LIB LICENSE %{SOURCE19} docs/interop/qmp-spec.txt
mv ${RPM_BUILD_ROOT}%{_docdir}/qemu/qemu-doc.html $RPM_BUILD_ROOT%{qemudocdir}
mv ${RPM_BUILD_ROOT}%{_docdir}/qemu/qemu-doc.txt $RPM_BUILD_ROOT%{qemudocdir}
mv ${RPM_BUILD_ROOT}%{_docdir}/qemu/qemu-qmp-ref.html $RPM_BUILD_ROOT%{qemudocdir}
mv ${RPM_BUILD_ROOT}%{_docdir}/qemu/qemu-qmp-ref.txt $RPM_BUILD_ROOT%{qemudocdir}
chmod -x ${RPM_BUILD_ROOT}%{_mandir}/man1/*
chmod -x ${RPM_BUILD_ROOT}%{_mandir}/man8/*

install -D -p -m 0644 qemu.sasl $RPM_BUILD_ROOT%{_sysconfdir}/sasl2/%{pkgname}.conf

# Provided by package openbios
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/openbios-ppc
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/openbios-sparc32
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/openbios-sparc64
# Provided by package SLOF
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/slof.bin

# Remove unpackaged files.
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/palcode-clipper
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/petalogix*.dtb
rm -f ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/bamboo.dtb
rm -f ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/ppc_rom.bin
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/s390-zipl.rom
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/s390-ccw.img
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/s390-netboot.img
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/u-boot.e500
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/canyonlands.dtb
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/hppa-firmware.img
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/u-boot-sam460-20100605.bin

%ifnarch %{power64}
   rm -f ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/spapr-rtas.bin
   rm -f ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/skiboot.lid
   rm -f ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/qemu_vga.ndrv
%endif

%ifnarch x86_64
    rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/acpi-dsdt.aml
    rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/kvmvapic.bin
    rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/linuxboot.bin
    rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/multiboot.bin
%endif

# Remove sparc files
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/QEMU,tcx.bin
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/QEMU,cgthree.bin

# Remove efi roms
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/efi*.rom

# Remove ivshmem example programs
rm -rf ${RPM_BUILD_ROOT}%{_bindir}/ivshmem-client
rm -rf ${RPM_BUILD_ROOT}%{_bindir}/ivshmem-server

# Provided by package ipxe
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/pxe*rom
# Provided by package vgabios
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/vgabios*bin
# Provided by package seabios
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/bios*.bin
# Provided by package sgabios
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/sgabios.bin

# Remove tracing stuff
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{pkgname}/trace-events-all

# the pxe gpxe images will be symlinks to the images on
# /usr/share/ipxe, as QEMU doesn't know how to look
# for other paths, yet.
pxe_link() {
    ln -s ../ipxe/$2.rom %{buildroot}%{_datadir}/%{pkgname}/pxe-$1.rom
}

%ifnarch aarch64
pxe_link e1000 8086100e
pxe_link ne2k_pci 10ec8029
pxe_link pcnet 10222000
pxe_link rtl8139 10ec8139
pxe_link virtio 1af41000
pxe_link e1000e 808610d3
%endif

rom_link() {
    ln -s $1 %{buildroot}%{_datadir}/%{pkgname}/$2
}

%ifnarch aarch64
  rom_link ../seavgabios/vgabios-isavga.bin vgabios.bin
  rom_link ../seavgabios/vgabios-cirrus.bin vgabios-cirrus.bin
  rom_link ../seavgabios/vgabios-qxl.bin vgabios-qxl.bin
  rom_link ../seavgabios/vgabios-stdvga.bin vgabios-stdvga.bin
  rom_link ../seavgabios/vgabios-vmware.bin vgabios-vmware.bin
  rom_link ../seavgabios/vgabios-virtio.bin vgabios-virtio.bin
%endif
%ifarch x86_64
  rom_link ../seabios/bios.bin bios.bin
  rom_link ../seabios/bios-256k.bin bios-256k.bin
  rom_link ../sgabios/sgabios.bin sgabios.bin
%endif

%if 0%{have_kvm_setup}
    install -D -p -m 755 %{SOURCE21} $RPM_BUILD_ROOT%{_prefix}/lib/systemd/kvm-setup
    install -D -p -m 644 %{SOURCE22} $RPM_BUILD_ROOT%{_unitdir}/kvm-setup.service
    install -D -p -m 644 %{SOURCE23} $RPM_BUILD_ROOT%{_presetdir}/85-kvm.preset
%endif

%if 0%{have_memlock_limits}
    install -D -p -m 644 %{SOURCE28} $RPM_BUILD_ROOT%{_sysconfdir}/security/limits.d/95-kvm-memlock.conf
%endif

# Install rules to use the bridge helper with libvirt's virbr0
install -D -m 0644 %{SOURCE12} $RPM_BUILD_ROOT%{_sysconfdir}/%{pkgname}/bridge.conf

%if 0
make %{?_smp_mflags} $buildldflags DESTDIR=$RPM_BUILD_ROOT install-libcacard

find $RPM_BUILD_ROOT -name "libcacard.so*" -exec chmod +x \{\} \;
%endif

find $RPM_BUILD_ROOT -name '*.la' -or -name '*.a' | xargs rm -f

# WRS
install -d %{buildroot}/etc/init.d
install -m 700 %{SOURCE127} %{buildroot}/etc/init.d/qemu_clean
install -d %{buildroot}/etc/systemd/system/
install -m 664 %{SOURCE128} %{buildroot}/etc/systemd/system/qemu_clean.service

%check
# WRS: Disable unit tests
# make check V=1

%post
# load kvm modules now, so we can make sure no reboot is needed.
# If there's already a kvm module installed, we don't mess with it
%udev_rules_update
sh %{_sysconfdir}/sysconfig/modules/kvm.modules &> /dev/null || :
    udevadm trigger --subsystem-match=misc --sysname-match=kvm --action=add || :
%if %{have_kvm_setup}
    systemctl daemon-reload # Make sure it sees the new presets and unitfile
    %systemd_post kvm-setup.service
    if systemctl is-enabled kvm-setup.service > /dev/null; then
        systemctl start kvm-setup.service
    fi
%endif

%post -n qemu-kvm-common%{?pkgsuffix}
# %systemd_post ksm.service
# %systemd_post ksmtuned.service

getent group kvm >/dev/null || groupadd -g 36 -r kvm
getent group qemu >/dev/null || groupadd -g 107 -r qemu
getent passwd qemu >/dev/null || \
useradd -r -u 107 -g qemu -G kvm -d / -s /sbin/nologin \
  -c "qemu user" qemu

# WRS
if [ $1 -eq 1 ] ; then
    ln -s /usr/libexec/qemu-kvm /usr/bin/qemu-system-x86_64
fi
exit 0

%systemd_post qemu_clean.service

%preun -n qemu-kvm-common%{?pkgsuffix}
# %systemd_preun ksm.service
# %systemd_preun ksmtuned.service

# WRS
%systemd_preun qemu_clean.service

%postun -n qemu-kvm-common%{?pkgsuffix}
# %systemd_postun_with_restart ksm.service
# %systemd_postun_with_restart ksmtuned.service

# WRS
%systemd_postun_with_restart qemu_clean.service

%global kvm_files \
%{_udevdir}/80-kvm.rules

%global qemu_kvm_files \
%{_libexecdir}/qemu-kvm \
%{_datadir}/%{pkgname}/systemtap/conf.d/qemu_kvm.conf \
%{_datadir}/%{pkgname}/systemtap/script.d/qemu_kvm.stp

# WRS: Disable traces
# %{_datadir}/systemtap/tapset/qemu-kvm.stp
# %{_datadir}/systemtap/tapset/qemu-kvm-simpletrace.stp

%files -n qemu-kvm-common%{?pkgsuffix}
%defattr(-,root,root)
%dir %{qemudocdir}
%doc %{qemudocdir}/Changelog
%doc %{qemudocdir}/README
%doc %{qemudocdir}/qemu-doc.html
%doc %{qemudocdir}/qemu-doc.txt
%doc %{qemudocdir}/COPYING
%doc %{qemudocdir}/COPYING.LIB
%doc %{qemudocdir}/LICENSE
%doc %{qemudocdir}/README.rhel6-gpxe-source
%doc %{qemudocdir}/README.systemtap
%doc %{qemudocdir}/qmp-spec.txt
%doc %{qemudocdir}/qemu-qmp-ref.html
%doc %{qemudocdir}/qemu-qmp-ref.txt

%dir %{_datadir}/%{pkgname}/
%{_datadir}/%{pkgname}/keymaps/
%{_mandir}/man1/%{pkgname}.1*
%{_mandir}/man7/qemu-qmp-ref*
%attr(4755, -, -) %{_libexecdir}/qemu-bridge-helper
%config(noreplace) %{_sysconfdir}/sasl2/%{pkgname}.conf
# %{_unitdir}/ksm.service
# %{_libexecdir}/ksmctl
# %config(noreplace) %{_sysconfdir}/sysconfig/ksm
# %{_unitdir}/ksmtuned.service
# %{_sbindir}/ksmtuned
# %config(noreplace) %{_sysconfdir}/ksmtuned.conf
%dir %{_sysconfdir}/%{pkgname}
%config(noreplace) %{_sysconfdir}/%{pkgname}/bridge.conf
%config(noreplace) %{_sysconfdir}/modprobe.d/vhost.conf
%{_sysconfdir}/modprobe.d/qemu-system-x86.conf
# WRS: Disable traces
# %{_datadir}/%{pkgname}/simpletrace.py*
# %{_datadir}/%{pkgname}/tracetool/*.py*
# %{_datadir}/%{pkgname}/tracetool/backend/*.py*
# %{_datadir}/%{pkgname}/tracetool/format/*.py*

%files
%defattr(-,root,root)
%ifarch x86_64
#   %{_datadir}/%{pkgname}/acpi-dsdt.aml
    %{_datadir}/%{pkgname}/bios.bin
    %{_datadir}/%{pkgname}/bios-256k.bin
    %{_datadir}/%{pkgname}/linuxboot.bin
    %{_datadir}/%{pkgname}/linuxboot_dma.bin
    %{_datadir}/%{pkgname}/multiboot.bin
    %{_datadir}/%{pkgname}/kvmvapic.bin
    %{_datadir}/%{pkgname}/sgabios.bin
%endif
%ifnarch aarch64
    %{_datadir}/%{pkgname}/vgabios.bin
    %{_datadir}/%{pkgname}/vgabios-cirrus.bin
    %{_datadir}/%{pkgname}/vgabios-qxl.bin
    %{_datadir}/%{pkgname}/vgabios-stdvga.bin
    %{_datadir}/%{pkgname}/vgabios-vmware.bin
    %{_datadir}/%{pkgname}/vgabios-virtio.bin
    %{_datadir}/%{pkgname}/pxe-e1000.rom
    %{_datadir}/%{pkgname}/pxe-e1000e.rom
    %{_datadir}/%{pkgname}/pxe-virtio.rom
    %{_datadir}/%{pkgname}/pxe-pcnet.rom
    %{_datadir}/%{pkgname}/pxe-rtl8139.rom
    %{_datadir}/%{pkgname}/pxe-ne2k_pci.rom
%endif
%{_datadir}/%{pkgname}/qemu-icon.bmp
%{_datadir}/%{pkgname}/qemu_logo_no_text.svg
%{_datadir}/%{pkgname}/rhel6-virtio.rom
%{_datadir}/%{pkgname}/rhel6-pcnet.rom
%{_datadir}/%{pkgname}/rhel6-rtl8139.rom
%{_datadir}/%{pkgname}/rhel6-ne2k_pci.rom
%{_datadir}/%{pkgname}/rhel6-e1000.rom
%{_datadir}/%{pkgname}/dump-guest-memory.py*
%ifarch %{power64}
    %{_datadir}/%{pkgname}/spapr-rtas.bin
%endif
%{?kvm_files:}
%{?qemu_kvm_files:}
%if %{have_kvm_setup}
    %{_prefix}/lib/systemd/kvm-setup
    %{_unitdir}/kvm-setup.service
    %{_presetdir}/85-kvm.preset
%endif
%if 0%{have_memlock_limits}
    %{_sysconfdir}/security/limits.d/95-kvm-memlock.conf
%endif

# WRS
/etc/init.d/qemu_clean
/etc/systemd/system/qemu_clean.service
/usr/bin/virtfs-proxy-helper
/usr/bin/kvm

%files -n qemu-kvm-tools%{?pkgsuffix}
%defattr(-,root,root,-)
%ifarch x86_64
%{_datadir}/%{pkgname}/tscdeadline_latency.flat
%endif

%files -n qemu-img%{?pkgsuffix}
%defattr(-,root,root)
%{_bindir}/qemu-img
%{_bindir}/qemu-io
%{_bindir}/qemu-nbd
%{_bindir}/qemu-pr-helper
%{_mandir}/man1/qemu-img.1*
%{_mandir}/man7/qemu-block-drivers.7*
%{_mandir}/man8/qemu-nbd.8*
# WRS: virtfs
%{_mandir}/man1/virtfs-proxy-helper.1*

%if 0
%files -n libcacard%{?pkgsuffix}
%defattr(-,root,root,-)
%{_libdir}/libcacard.so.*

%files -n libcacard-tools%{?pkgsuffix}
%defattr(-,root,root,-)
%{_bindir}/vscclient

%files -n libcacard-devel%{?pkgsuffix}
%defattr(-,root,root,-)
%{_includedir}/cacard
%{_libdir}/libcacard.so
%{_libdir}/pkgconfig/libcacard.pc
%endif

%changelog
* Thu Apr 20 2017 Sandro Bonazzola <sbonazzo@redhat.com> - ev-2.6.0-28.el7_3.9.1
- Removing RH branding from package name

* Fri Mar 24 2017 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-28.el7_3.9
- kvm-block-gluster-memory-usage-use-one-glfs-instance-per.patch [bz#1413044]
- kvm-gluster-Fix-use-after-free-in-glfs_clear_preopened.patch [bz#1413044]
- kvm-fix-cirrus_vga-fix-OOB-read-case-qemu-Segmentation-f.patch [bz#1430061]
- kvm-cirrus-vnc-zap-bitblit-support-from-console-code.patch [bz#1430061]
- kvm-cirrus-add-option-to-disable-blitter.patch [bz#1430061]
- kvm-cirrus-fix-cirrus_invalidate_region.patch [bz#1430061]
- kvm-cirrus-stop-passing-around-dst-pointers-in-the-blitt.patch [bz#1430061]
- kvm-cirrus-stop-passing-around-src-pointers-in-the-blitt.patch [bz#1430061]
- kvm-cirrus-fix-off-by-one-in-cirrus_bitblt_rop_bkwd_tran.patch [bz#1430061]
- kvm-file-posix-Consider-max_segments-for-BlockLimits.max.patch [bz#1431149]
- kvm-file-posix-clean-up-max_segments-buffer-termination.patch [bz#1431149]
- kvm-file-posix-Don-t-leak-fd-in-hdev_get_max_segments.patch [bz#1431149]
- Resolves: bz#1413044
  (block-gluster: use one glfs instance per volume)
- Resolves: bz#1430061
  (CVE-2016-9603 qemu-kvm-rhev: Qemu: cirrus: heap buffer overflow via vnc connection [rhel-7.3.z])
- Resolves: bz#1431149
  (VMs pause when writing to Virtio-SCSI direct lun with scsi passthrough enabled via an Emulex HBA)

* Tue Mar 21 2017 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-28.el7_3.8
- kvm-target-i386-present-virtual-L3-cache-info-for-vcpus.patch [bz#1430802]
- Resolves: bz#1430802
  (Enhance qemu to present virtual L3 cache info for vcpus)

* Wed Mar 15 2017 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-28.el7_3.7
- kvm-block-check-full-backing-filename-when-searching-pro.patch [bz#1425125]
- kvm-qemu-iotests-Don-t-create-fifos-pidfiles-with-protoc.patch [bz#1425125]
- kvm-qemu-iotest-test-to-lookup-protocol-based-image-with.patch [bz#1425125]
- kvm-target-i386-Don-t-use-cpu-migratable-when-filtering-.patch [bz#1413897]
- Resolves: bz#1413897
  (cpu flag nonstop_tsc is not present in guest with host-passthrough and feature policy require invtsc)
- Resolves: bz#1425125
  (qemu fails to recognize gluster URIs in backing chain for block-commit operation)

* Mon Feb 13 2017 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-28.el7_3.6
- kvm-cirrus-fix-patterncopy-checks.patch [bz#1420493]
- kvm-Revert-cirrus-allow-zero-source-pitch-in-pattern-fil.patch [bz#1420493]
- kvm-cirrus-add-blit_is_unsafe-call-to-cirrus_bitblt_cput.patch [bz#1420493]
- Resolves: bz#1420493
  (EMBARGOED CVE-2017-2620 qemu-kvm-rhev: Qemu: display: cirrus: potential arbitrary code execution via cirrus_bitblt_cputovideo [rhel-7.3.z])

* Fri Feb 10 2017 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-28.el7_3.5
- kvm-memory-Provide-memory_region_init_rom.patch [bz#1420456]
- kvm-pci-mark-ROMs-read-only.patch [bz#1420456]
- kvm-vhost-skip-ROM-sections.patch [bz#1420456]
- kvm-display-cirrus-check-vga-bits-per-pixel-bpp-value.patch [bz#1418234]
- kvm-display-cirrus-ignore-source-pitch-value-as-needed-i.patch [bz#1418234]
- kvm-cirrus-handle-negative-pitch-in-cirrus_invalidate_re.patch [bz#1418234]
- kvm-cirrus-allow-zero-source-pitch-in-pattern-fill-rops.patch [bz#1418234]
- kvm-cirrus-fix-blit-address-mask-handling.patch [bz#1418234]
- kvm-cirrus-fix-oob-access-issue-CVE-2017-2615.patch [bz#1418234]
- Resolves: bz#1418234
  (CVE-2017-2615 qemu-kvm-rhev: Qemu: display: cirrus: oob access while doing bitblt copy backward mode [rhel-7.3.z])
- Resolves: bz#1420456
  ([ppc64le]reset vm when do migration, HMP in src host promp "tcmalloc: large alloc 1073872896 bytes...")

* Wed Feb 08 2017 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-28.el7_3.4
- kvm-Disable-usbredir-and-libcacard-for-unsupported-archi.patch [bz#1420428]
- Resolves: bz#1420428
  (Remove dependencies required by spice on ppc64le)

* Wed Jan 04 2017 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-28.el7_3.3
- kvm-pc_piix-fix-compat-props-typo-for-RHEL6-machine-type.patch [bz#1408122]
- kvm-net-don-t-poke-at-chardev-internal-QemuOpts.patch [bz#1410200]
- Resolves: bz#1408122
  (Opteron_G4 CPU model broken in QEMU 2.6 with RHEL 6 machine type)
- Resolves: bz#1410200
  (qemu gets SIGSEGV when hot-plug a vhostuser network)

* Fri Dec 09 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-28.el7_3.2
- kvm-numa-do-not-leak-NumaOptions.patch [bz#1397745]
- kvm-char-free-the-tcp-connection-data-when-closing.patch [bz#1397745]
- kvm-char-free-MuxDriver-when-closing.patch [bz#1397745]
- kvm-ahci-free-irqs-array.patch [bz#1397745]
- kvm-virtio-input-free-config-list.patch [bz#1397745]
- kvm-usb-free-USBDevice.strings.patch [bz#1397745]
- kvm-usb-free-leaking-path.patch [bz#1397745]
- kvm-ahci-fix-sglist-leak-on-retry.patch [bz#1397745]
- kvm-virtio-add-virtqueue_rewind.patch [bz#1402509]
- kvm-virtio-balloon-fix-stats-vq-migration.patch [bz#1402509]
- kvm-virtio-blk-Release-s-rq-queue-at-system_reset.patch [bz#1393041]
- kvm-virtio-blk-Remove-stale-comment-about-draining.patch [bz#1393041]
- Resolves: bz#1393041
  (system_reset should clear pending request for error (virtio-blk))
- Resolves: bz#1397745
  (Backport memory leak fixes from QEMU 2.7)
- Resolves: bz#1402509
  (virtio-balloon stats virtqueue does not migrate properly)

* Wed Nov 30 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-28.el7_3.1
- kvm-ide-fix-halted-IO-segfault-at-reset.patch [bz#1393043]
- kvm-atapi-fix-halted-DMA-reset.patch [bz#1393043]
- kvm-ahci-clear-aiocb-in-ncq_cb.patch [bz#1393736]
- kvm-Workaround-rhel6-ctrl_guest_offloads-machine-type-mi.patch [bz#1392876]
- kvm-Postcopy-vs-xbzrle-Don-t-send-xbzrle-pages-once-in-p.patch [bz#1395360]
- kvm-ui-fix-refresh-of-VNC-server-surface.patch [bz#1392881]
- Resolves: bz#1392876
  (windows guests migration from rhel6.8-z to rhel7.3 with virtio-net-pci fail)
- Resolves: bz#1392881
  (Graphic can't be showed out quickly if guest graphic mode is vnc)
- Resolves: bz#1393043
  (system_reset should clear pending request for error (IDE))
- Resolves: bz#1393736
  (qemu core dump when there is an I/O error on AHCI)
- Resolves: bz#1395360
  (Post-copy migration fails with XBZRLE compression)

* Tue Sep 27 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-28.el7
- kvm-ARM-ACPI-fix-the-AML-ID-format-for-CPU-devices.patch [bz#1373733]
- Resolves: bz#1373733
  (failed to run a guest VM with >= 12 vcpu under ACPI mode)

* Fri Sep 23 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-27.el7
- kvm-char-fix-waiting-for-TLS-and-telnet-connection.patch [bz#1300773]
- kvm-target-i386-introduce-kvm_put_one_msr.patch [bz#1377920]
- kvm-apic-set-APIC-base-as-part-of-kvm_apic_put.patch [bz#1377920]
- Resolves: bz#1300773
  (RFE: add support for native TLS encryption on chardev  TCP transports)
- Resolves: bz#1377920
  (Guest fails reboot and causes kernel-panic)

* Tue Sep 20 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-26.el7
- kvm-target-i386-Add-more-Intel-AVX-512-instructions-supp.patch [bz#1372455]
- kvm-iothread-Stop-threads-before-main-quits.patch [bz#1343021]
- kvm-virtio-pci-error-out-when-both-legacy-and-modern-mod.patch [bz#1370005]
- kvm-virtio-bus-Plug-devices-after-features-are-negotiate.patch [bz#1370005]
- kvm-virtio-pci-reduce-modern_mem_bar-size.patch [bz#1365613]
- kvm-virtio-vga-adapt-to-page-per-vq-off.patch [bz#1365613]
- kvm-virtio-gpu-pci-tag-as-not-hotpluggable.patch [bz#1368032]
- kvm-scsi-disk-Cleaning-up-around-tray-open-state.patch [bz#1374251]
- kvm-virtio-scsi-Don-t-abort-when-media-is-ejected.patch [bz#1374251]
- kvm-io-remove-mistaken-call-to-object_ref-on-QTask.patch [bz#1375677]
- kvm-block-Invalidate-all-children.patch [bz#1355927]
- kvm-block-Drop-superfluous-invalidating-bs-file-from-dri.patch [bz#1355927]
- kvm-block-Inactivate-all-children.patch [bz#1355927]
- kvm-vfio-pci-Fix-regression-in-MSI-routing-configuration.patch [bz#1373802]
- kvm-x86-lapic-Load-LAPIC-state-at-post_load.patch [bz#1363998]
- kvm-blockdev-ignore-cache-options-for-empty-CDROM-drives.patch [bz#1342999]
- kvm-block-reintroduce-bdrv_flush_all.patch [bz#1338638]
- kvm-qemu-use-bdrv_flush_all-for-vm_stop-et-al.patch [bz#1338638]
- Resolves: bz#1338638
  (Migration fails after ejecting the cdrom in the guest)
- Resolves: bz#1342999
  ('cache=x' cannot work with empty cdrom)
- Resolves: bz#1343021
  (Core dump when quit from HMP after migration finished)
- Resolves: bz#1355927
  (qemu SIGABRT when doing inactive blockcommit with external system checkpoint snapshot)
- Resolves: bz#1363998
  (Live  migration via a compressed file  causes the guest desktop to freeze)
- Resolves: bz#1365613
  ([PCI] The default MMIO range reserved by firmware for PCI bridges is not enough to hotplug virtio-1 devices)
- Resolves: bz#1368032
  (kernel crash after hot remove virtio-gpu device)
- Resolves: bz#1370005
  (Fail to get network device info(eth0) in guest with virtio-net-pci/vhostforce)
- Resolves: bz#1372455
  ([Intel 7.3 Bug] SKL-SP Guest cpu doesn't support avx512 instruction sets(avx512bw, avx512dq and avx512vl)(qemu-kvm-rhev))
- Resolves: bz#1373802
  (Network can't recover when trigger EEH  one time)
- Resolves: bz#1374251
  (qemu-kvm-rhev core dumped when enabling virtio-scsi "data plane" and executing "eject")
- Resolves: bz#1375677
  (Crash when performing VNC websockets handshake)

* Tue Sep 13 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-25.el7
- kvm-virtio-recalculate-vq-inuse-after-migration.patch [bz#1372763]
- kvm-virtio-decrement-vq-inuse-in-virtqueue_discard.patch [bz#1372763]
- kvm-virtio-balloon-discard-virtqueue-element-on-reset.patch [bz#1370703]
- kvm-virtio-zero-vq-inuse-in-virtio_reset.patch [bz#1370703 bz#1374623]
- Resolves: bz#1370703
  ([Balloon] Whql Job "Commom scenario stress with IO" failed on 2008-32/64)
- Resolves: bz#1372763
  (RHSA-2016-1756 breaks migration of instances)
- Resolves: bz#1374623
  (RHSA-2016-1756 breaks migration of instances)

* Fri Sep 09 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-24.el7
- kvm-Fix-configure-test-for-PBKDF2-in-nettle.patch [bz#1301019]
- kvm-redhat-switch-from-gcrypt-to-nettle-for-crypto.patch [bz#1301019]
- kvm-crypto-assert-that-qcrypto_hash_digest_len-is-in-ran.patch [bz#1301019]
- kvm-crypto-fix-handling-of-iv-generator-hash-defaults.patch [bz#1301019]
- kvm-crypto-ensure-XTS-is-only-used-with-ciphers-with-16-.patch [bz#1301019]
- kvm-vhost-user-test-Use-libqos-instead-of-pxe-virtio.rom.patch [bz#1371211]
- kvm-vl-Delay-initialization-of-memory-backends.patch [bz#1371211]
- kvm-spapr-implement-H_CHANGE_LOGICAL_LAN_MAC-h_call.patch [bz#1371419]
- Resolves: bz#1301019
  (RFE: add support for LUKS disk encryption format driver w/ RBD, iSCSI, and qcow2)
- Resolves: bz#1371211
  (Qemu 2.6 won't boot guest with 2 meg hugepages)
- Resolves: bz#1371419
  ([ppc64le] Can't modify mac address for spapr-vlan device in rhel6.8 guest)

* Tue Sep 06 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-23.el7
- kvm-vhost-user-disconnect-on-HUP.patch [bz#1355902]
- kvm-vhost-don-t-assume-opaque-is-a-fd-use-backend-cleanu.patch [bz#1355902]
- kvm-vhost-make-vhost_log_put-idempotent.patch [bz#1355902]
- kvm-vhost-assert-the-log-was-cleaned-up.patch [bz#1355902]
- kvm-vhost-fix-cleanup-on-not-fully-initialized-device.patch [bz#1355902]
- kvm-vhost-make-vhost_dev_cleanup-idempotent.patch [bz#1355902]
- kvm-vhost-net-always-call-vhost_dev_cleanup-on-failure.patch [bz#1355902]
- kvm-vhost-fix-calling-vhost_dev_cleanup-after-vhost_dev_.patch [bz#1355902]
- kvm-vhost-do-not-assert-on-vhost_ops-failure.patch [bz#1355902]
- kvm-vhost-add-missing-VHOST_OPS_DEBUG.patch [bz#1355902]
- kvm-vhost-use-error_report-instead-of-fprintf-stderr.patch [bz#1355902]
- kvm-qemu-char-fix-qemu_chr_fe_set_msgfds-crash-when-disc.patch [bz#1355902]
- kvm-vhost-user-call-set_msgfds-unconditionally.patch [bz#1355902]
- kvm-vhost-user-check-qemu_chr_fe_set_msgfds-return-value.patch [bz#1355902]
- kvm-vhost-user-check-vhost_user_-read-write-return-value.patch [bz#1355902]
- kvm-vhost-user-keep-vhost_net-after-a-disconnection.patch [bz#1355902]
- kvm-vhost-user-add-get_vhost_net-assertions.patch [bz#1355902]
- kvm-Revert-vhost-net-do-not-crash-if-backend-is-not-pres.patch [bz#1355902]
- kvm-vhost-net-vhost_migration_done-is-vhost-user-specifi.patch [bz#1355902]
- kvm-vhost-add-assert-to-check-runtime-behaviour.patch [bz#1355902]
- kvm-char-add-chr_wait_connected-callback.patch [bz#1355902]
- kvm-char-add-and-use-tcp_chr_wait_connected.patch [bz#1355902]
- kvm-vhost-user-wait-until-backend-init-is-completed.patch [bz#1355902]
- kvm-vhost-user-add-error-report-in-vhost_user_write.patch [bz#1355902]
- kvm-vhost-add-vhost_net_set_backend.patch [bz#1355902]
- kvm-vhost-do-not-update-last-avail-idx-on-get_vring_base.patch [bz#1355902]
- kvm-vhost-check-for-vhost_ops-before-using.patch [bz#1355902]
- kvm-vhost-user-Introduce-a-new-protocol-feature-REPLY_AC.patch [bz#1355902]
- kvm-linux-aio-Handle-io_submit-failure-gracefully.patch [bz#1285928]
- kvm-Revert-acpi-pc-add-fw_cfg-device-node-to-dsdt.patch [bz#1368153]
- Resolves: bz#1285928
  (linux-aio aborts on io_submit() failure)
- Resolves: bz#1355902
  (vhost-user reconnect misc fixes and improvements)
- Resolves: bz#1368153
  (Please hide fw_cfg device in windows guest in order to make svvp test pass)

* Mon Aug 22 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-22.el7
- kvm-target-i386-kvm-Report-kvm_pv_unhalt-as-unsupported-.patch [bz#1363679]
- kvm-ioapic-keep-RO-bits-for-IOAPIC-entry.patch [bz#1358653]
- kvm-ioapic-clear-remote-irr-bit-for-edge-triggered-inter.patch [bz#1358653]
- kvm-x86-iommu-introduce-parent-class.patch [bz#1358653]
- kvm-intel_iommu-rename-VTD_PCI_DEVFN_MAX-to-x86-iommu.patch [bz#1358653]
- kvm-x86-iommu-provide-x86_iommu_get_default.patch [bz#1358653]
- kvm-x86-iommu-introduce-intremap-property.patch [bz#1358653]
- kvm-acpi-enable-INTR-for-DMAR-report-structure.patch [bz#1358653]
- kvm-intel_iommu-allow-queued-invalidation-for-IR.patch [bz#1358653]
- kvm-intel_iommu-set-IR-bit-for-ECAP-register.patch [bz#1358653]
- kvm-acpi-add-DMAR-scope-definition-for-root-IOAPIC.patch [bz#1358653]
- kvm-intel_iommu-define-interrupt-remap-table-addr-regist.patch [bz#1358653]
- kvm-intel_iommu-handle-interrupt-remap-enable.patch [bz#1358653]
- kvm-intel_iommu-define-several-structs-for-IOMMU-IR.patch [bz#1358653]
- kvm-intel_iommu-add-IR-translation-faults-defines.patch [bz#1358653]
- kvm-intel_iommu-Add-support-for-PCI-MSI-remap.patch [bz#1358653]
- kvm-intel_iommu-get-rid-of-0-initializers.patch [bz#1358653]
- kvm-q35-ioapic-add-support-for-emulated-IOAPIC-IR.patch [bz#1358653]
- kvm-ioapic-introduce-ioapic_entry_parse-helper.patch [bz#1358653]
- kvm-intel_iommu-add-support-for-split-irqchip.patch [bz#1358653]
- kvm-x86-iommu-introduce-IEC-notifiers.patch [bz#1358653]
- kvm-ioapic-register-IOMMU-IEC-notifier-for-ioapic.patch [bz#1358653]
- kvm-intel_iommu-Add-support-for-Extended-Interrupt-Mode.patch [bz#1358653]
- kvm-intel_iommu-add-SID-validation-for-IR.patch [bz#1358653]
- kvm-irqchip-simplify-kvm_irqchip_add_msi_route.patch [bz#1358653]
- kvm-irqchip-i386-add-hook-for-add-remove-virq.patch [bz#1358653]
- kvm-irqchip-x86-add-msi-route-notify-fn.patch [bz#1358653]
- kvm-irqchip-do-explicit-commit-when-update-irq.patch [bz#1358653]
- kvm-intel_iommu-support-all-masks-in-interrupt-entry-cac.patch [bz#1358653]
- kvm-all-add-trace-events-for-kvm-irqchip-ops.patch [bz#1358653]
- kvm-intel_iommu-disallow-kernel-irqchip-on-with-IR.patch [bz#1358653]
- kvm-intel_iommu-avoid-unnamed-fields.patch [bz#1358653]
- kvm-irqchip-only-commit-route-when-irqchip-is-used.patch [bz#1358653]
- kvm-x86-ioapic-ignore-level-irq-during-processing.patch [bz#1358653]
- kvm-x86-ioapic-add-support-for-explicit-EOI.patch [bz#1358653]
- kvm-memory-Fix-IOMMU-replay-base-address.patch [bz#1364035]
- kvm-Add-luks-to-block-driver-whitelist.patch [bz#1301019]
- Resolves: bz#1301019
  (RFE: add support for LUKS disk encryption format driver w/ RBD, iSCSI, and qcow2)
- Resolves: bz#1358653
  ([RFE] Interrupt remapping support for Intel vIOMMUs)
- Resolves: bz#1363679
  (RHEL guest hangs with kernel-irqchip=off and smp>1)
- Resolves: bz#1364035
  ([ppc64le][VFIO]Qemu complains:vfio_dma_map(0x10033d3a980, 0x1f34f0000, 0x10000, 0x3fff9a6d0000) = -6 (No such device or address))

* Tue Aug 16 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-21.el7
- kvm-fix-qemu-exit-on-memory-hotplug-when-allocation-fail.patch [bz#1351409]
- kvm-spapr-remove-extra-type-variable.patch [bz#1363812]
- kvm-ppc-Introduce-a-function-to-look-up-CPU-alias-string.patch [bz#1363812]
- kvm-hw-ppc-spapr-Look-up-CPU-alias-names-instead-of-hard.patch [bz#1363812]
- kvm-ppc-kvm-Do-not-mess-up-the-generic-CPU-family-regist.patch [bz#1363812]
- kvm-ppc-kvm-Register-also-a-generic-spapr-CPU-core-famil.patch [bz#1363812]
- kvm-ppc64-fix-compressed-dump-with-pseries-kernel.patch [bz#1240497]
- kvm-monitor-fix-crash-when-leaving-qemu-with-spice-audio.patch [bz#1355704]
- kvm-audio-clean-up-before-monitor-clean-up.patch [bz#1355704]
- kvm-vnc-don-t-crash-getting-server-info-if-lsock-is-NULL.patch [bz#1359655]
- kvm-vnc-fix-crash-when-vnc_server_info_get-has-an-error.patch [bz#1359655]
- kvm-vnc-ensure-connection-sharing-limits-is-always-confi.patch [bz#1359655]
- kvm-vnc-make-sure-we-finish-disconnect.patch [bz#1352799]
- kvm-virtio-net-allow-increasing-rx-queue-size.patch [bz#1358962]
- kvm-input-add-trace-events-for-full-queues.patch [bz#1366471]
- kvm-virtio-set-low-features-early-on-load.patch [bz#1365747]
- kvm-Revert-virtio-net-unbreak-self-announcement-and-gues.patch [bz#1365747]
- Resolves: bz#1240497
  (qemu-kvm-rhev: dump-guest-memory creates invalid header with format kdump-{zlib,lzo,snappy} on ppc64)
- Resolves: bz#1351409
  (When hotplug memory, guest will shutdown as Insufficient free host memory pages available to allocate)
- Resolves: bz#1352799
  (Client information from hmp doesn't vanish after client disconnect when using vnc display)
- Resolves: bz#1355704
  (spice: core dump when 'quit')
- Resolves: bz#1358962
  (Increase the queue size to the max allowed, 1024.)
- Resolves: bz#1359655
  (Qemu crashes when connecting to a guest started with "-vnc none" by virt-viewer)
- Resolves: bz#1363812
  (qemu-kvm-rhev: -cpu POWER8 no longer works)
- Resolves: bz#1365747
  (Migrate guest(win10) after hot plug/unplug memory balloon device [Missing section footer for 0000:00:07.0/virtio-net])
- Resolves: bz#1366471
  (QEMU prints "usb-kbd: warning: key event queue full" when pressing keys during SLOF boot)

* Wed Aug 10 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-20.el7
- kvm-block-gluster-rename-server-volname-image-host-volum.patch [bz#1247933]
- kvm-block-gluster-code-cleanup.patch [bz#1247933]
- kvm-block-gluster-deprecate-rdma-support.patch [bz#1247933]
- kvm-block-gluster-using-new-qapi-schema.patch [bz#1247933]
- kvm-block-gluster-add-support-for-multiple-gluster-serve.patch [bz#1247933]
- kvm-block-gluster-fix-doc-in-the-qapi-schema-and-member-.patch [bz#1247933]
- kvm-throttle-Don-t-allow-burst-limits-to-be-lower-than-t.patch [bz#1355665]
- kvm-throttle-Test-burst-limits-lower-than-the-normal-lim.patch [bz#1355665]
- kvm-spapr-Error-out-when-CPU-hotplug-is-attempted-on-old.patch [bz#1362019]
- kvm-spapr-Correctly-set-query_hotpluggable_cpus-hook-bas.patch [bz#1362019]
- Resolves: bz#1247933
  (RFE: qemu-kvm-rhev: support multiple volume hosts for gluster volumes)
- Resolves: bz#1355665
  (Suggest to limit the burst value to be not less than the throttle value)
- Resolves: bz#1362019
  (Crashes when using query-hotpluggable-cpus with pseries-rhel7.2.0 machine type)

* Fri Aug 05 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-19.el7
- kvm-hw-pcie-root-port-Fix-PCIe-root-port-initialization.patch [bz#1323976]
- kvm-hw-pxb-declare-pxb-devices-as-not-hot-pluggable.patch [bz#1323976]
- kvm-hw-acpi-fix-a-DSDT-table-issue-when-a-pxb-is-present.patch [bz#1323976]
- kvm-acpi-refactor-pxb-crs-computation.patch [bz#1323976]
- kvm-hw-apci-handle-64-bit-MMIO-regions-correctly.patch [bz#1323976]
- kvm-target-i386-Move-TCG-initialization-check-to-tcg_x86.patch [bz#1087672]
- kvm-target-i386-Move-TCG-initialization-to-realize-time.patch [bz#1087672]
- kvm-target-i386-Call-cpu_exec_init-on-realize.patch [bz#1087672]
- kvm-tests-acpi-report-names-of-expected-files-in-verbose.patch [bz#1087672]
- kvm-acpi-add-aml_debug.patch [bz#1087672]
- kvm-acpi-add-aml_refof.patch [bz#1087672]
- kvm-pc-acpi-remove-AML-for-empty-not-used-GPE-handlers.patch [bz#1087672]
- kvm-pc-acpi-consolidate-CPU-hotplug-AML.patch [bz#1087672]
- kvm-pc-acpi-consolidate-GPE._E02-with-the-rest-of-CPU-ho.patch [bz#1087672]
- kvm-pc-acpi-cpu-hotplug-make-AML-CPU_foo-defines-local-t.patch [bz#1087672]
- kvm-pc-acpi-mark-current-CPU-hotplug-functions-as-legacy.patch [bz#1087672]
- kvm-pc-acpi-consolidate-legacy-CPU-hotplug-in-one-file.patch [bz#1087672]
- kvm-pc-acpi-simplify-build_legacy_cpu_hotplug_aml-signat.patch [bz#1087672]
- kvm-pc-acpi-cpuhp-legacy-switch-ProcessorID-to-possible_.patch [bz#1087672]
- kvm-acpi-extend-ACPI-interface-to-provide-send_event-hoo.patch [bz#1087672]
- kvm-pc-use-AcpiDeviceIfClass.send_event-to-issue-GPE-eve.patch [bz#1087672]
- kvm-target-i386-Remove-xlevel-hv-spinlocks-option-fixups.patch [bz#1087672]
- kvm-target-i386-Move-features-logic-that-requires-CPUSta.patch [bz#1087672]
- kvm-target-i386-Remove-assert-kvm_enabled-from-host_x86_.patch [bz#1087672]
- kvm-target-i386-Move-xcc-kvm_required-check-to-realize-t.patch [bz#1087672]
- kvm-target-i386-Use-cpu_generic_init-in-cpu_x86_init.patch [bz#1087672]
- kvm-target-i386-Consolidate-calls-of-object_property_par.patch [bz#1087672]
- kvm-docs-update-ACPI-CPU-hotplug-spec-with-new-protocol.patch [bz#1087672]
- kvm-pc-piix4-ich9-add-cpu-hotplug-legacy-property.patch [bz#1087672]
- kvm-acpi-cpuhp-add-CPU-devices-AML-with-_STA-method.patch [bz#1087672]
- kvm-pc-acpi-introduce-AcpiDeviceIfClass.madt_cpu-hook.patch [bz#1087672]
- kvm-acpi-cpuhp-implement-hot-add-parts-of-CPU-hotplug-in.patch [bz#1087672]
- kvm-acpi-cpuhp-implement-hot-remove-parts-of-CPU-hotplug.patch [bz#1087672]
- kvm-acpi-cpuhp-add-cpu._OST-handling.patch [bz#1087672]
- kvm-pc-use-new-CPU-hotplug-interface-since-2.7-machine-t.patch [bz#1087672]
- kvm-pc-acpi-drop-intermediate-PCMachineState.node_cpu.patch [bz#1087672]
- kvm-qmp-fix-spapr-example-of-query-hotpluggable-cpus.patch [bz#1087672]
- kvm-qdev-Don-t-stop-applying-globals-on-first-error.patch [bz#1087672]
- kvm-qdev-Eliminate-qemu_add_globals-function.patch [bz#1087672]
- kvm-qdev-Use-GList-for-global-properties.patch [bz#1087672]
- kvm-qdev-GlobalProperty.errp-field.patch [bz#1087672]
- kvm-vl-Simplify-global-property-registration.patch [bz#1087672]
- kvm-machine-add-properties-to-compat_props-incrementaly.patch [bz#1087672]
- kvm-machine-Add-machine_register_compat_props-function.patch [bz#1087672]
- kvm-vl-Set-errp-to-error_abort-on-machine-compat_props.patch [bz#1087672]
- kvm-target-sparc-Use-sparc_cpu_parse_features-directly.patch [bz#1087672]
- kvm-target-i386-Avoid-using-locals-outside-their-scope.patch [bz#1087672]
- kvm-cpu-Use-CPUClass-parse_features-as-convertor-to-glob.patch [bz#1087672]
- kvm-arm-virt-Parse-cpu_model-only-once.patch [bz#1087672]
- kvm-cpu-make-cpu-qom.h-only-include-able-from-cpu.h.patch [bz#1087672]
- kvm-target-i386-make-cpu-qom.h-not-target-specific.patch [bz#1087672]
- kvm-target-Don-t-redefine-cpu_exec.patch [bz#1087672]
- kvm-pc-Parse-CPU-features-only-once.patch [bz#1087672]
- kvm-target-i386-Use-uint32_t-for-X86CPU.apic_id.patch [bz#1087672]
- kvm-pc-Add-x86_topo_ids_from_apicid.patch [bz#1087672]
- kvm-pc-Extract-CPU-lookup-into-a-separate-function.patch [bz#1087672]
- kvm-pc-cpu-Consolidate-apic-id-validity-checks-in-pc_cpu.patch [bz#1087672]
- kvm-target-i386-Replace-custom-apic-id-setter-getter-wit.patch [bz#1087672]
- kvm-target-i386-Add-socket-core-thread-properties-to-X86.patch [bz#1087672]
- kvm-target-i386-cpu-Do-not-ignore-error-and-fix-apic-par.patch [bz#1087672]
- kvm-target-i386-Fix-apic-object-leak-when-CPU-is-deleted.patch [bz#1087672]
- kvm-pc-Set-APIC-ID-based-on-socket-core-thread-ids-if-it.patch [bz#1087672]
- kvm-pc-Delay-setting-number-of-boot-CPUs-to-machine_done.patch [bz#1087672]
- kvm-pc-Register-created-initial-and-hotpluged-CPUs-in-on.patch [bz#1087672]
- kvm-pc-Forbid-BSP-removal.patch [bz#1087672]
- kvm-pc-Enforce-adding-CPUs-contiguously-and-removing-the.patch [bz#1087672]
- kvm-pc-cpu-Allow-device_add-to-be-used-with-x86-cpu.patch [bz#1087672]
- kvm-pc-Implement-query-hotpluggable-cpus-callback.patch [bz#1087672]
- kvm-apic-move-MAX_APICS-check-to-apic-class.patch [bz#1087672]
- kvm-apic-Drop-APICCommonState.idx-and-use-APIC-ID-as-ind.patch [bz#1087672]
- kvm-apic-kvm-apic-Fix-crash-due-to-access-to-freed-memor.patch [bz#1087672]
- kvm-apic-Add-unrealize-callbacks.patch [bz#1087672]
- kvm-apic-Use-apic_id-as-apic-s-migration-instance_id.patch [bz#1087672]
- kvm-target-i386-Add-x86_cpu_unrealizefn.patch [bz#1087672]
- kvm-pc-Make-device_del-CPU-work-for-x86-CPUs.patch [bz#1087672]
- kvm-exec-Reduce-CONFIG_USER_ONLY-ifdeffenery.patch [bz#1087672]
- kvm-exec-Don-t-use-cpu_index-to-detect-if-cpu_exec_init-.patch [bz#1087672]
- kvm-exec-Set-cpu_index-only-if-it-s-not-been-explictly-s.patch [bz#1087672]
- kvm-qdev-Fix-object-reference-leak-in-case-device.realiz.patch [bz#1087672]
- kvm-pc-Init-CPUState-cpu_index-with-index-in-possible_cp.patch [bz#1087672]
- kvm-Revert-pc-Enforce-adding-CPUs-contiguously-and-remov.patch [bz#1087672]
- kvm-qdev-ignore-GlobalProperty.errp-for-hotplugged-devic.patch [bz#1087672]
- kvm-vl-exit-if-a-bad-property-value-is-passed-to-global.patch [bz#1087672]
- kvm-apic-fix-broken-migration-for-kvm-apic.patch [bz#1087672]
- kvm-RHEL-only-hw-char-pl011-fix-SBSA-reset.patch [bz#1266048]
- kvm-migration-regain-control-of-images-when-migration-fa.patch [bz#1361539]
- kvm-migration-Promote-improved-autoconverge-commands-out.patch [bz#1358141]
- kvm-spapr-Ensure-CPU-cores-are-added-contiguously-and-re.patch [bz#1361443]
- kvm-spapr-disintricate-core-id-from-DT-semantics.patch [bz#1361443]
- kvm-spapr-init-CPUState-cpu_index-with-index-relative-to.patch [bz#1361443]
- kvm-Revert-spapr-Ensure-CPU-cores-are-added-contiguously.patch [bz#1361443]
- kvm-spapr-Prevent-boot-CPU-core-removal.patch [bz#1361443]
- kvm-virtio-vga-propagate-on-gpu-realized-error.patch [bz#1360664]
- kvm-hw-virtio-pci-fix-virtio-behaviour.patch [bz#1360664]
- kvm-q35-disable-s3-s4-by-default.patch [bz#1357202]
- kvm-pcie-fix-link-active-status-bit-migration.patch [bz#1352860]
- kvm-pc-rhel-7.2-pcie-fix-link-active-status-bit-migratio.patch [bz#1352860]
- kvm-add-e1000e-ipxe-rom-symlink.patch [bz#1343092]
- kvm-e1000e-add-boot-rom.patch [bz#1343092]
- Resolves: bz#1087672
  ([Fujitsu 7.2 FEAT]: qemu vcpu hot-remove support)
- Resolves: bz#1266048
  (login prompt does not work inside KVM guest when keys are pressed while the kernel is booting)
- Resolves: bz#1323976
  (PCI: Add 64-bit MMIO support to PXB devices)
- Resolves: bz#1343092
  (RFE: Integrate e1000e implementation in downstream QEMU)
- Resolves: bz#1352860
  (Migration is failed from host RHEL7.2.z to host RHEL7.3 with "-M pc-i440fx-rhel7.0.0 -device nec-usb-xhci")
- Resolves: bz#1357202
  ([Q35] S3 should be disabled by default for the pc-q35-rhel7.3.0 machine type)
- Resolves: bz#1358141
  (Removal of the "x-" prefix for dynamic cpu throttling)
- Resolves: bz#1360664
  ([virtio] Update default virtio-1 behavior for virtio devices)
- Resolves: bz#1361443
  (ppc64le: Introduce stable cpu_index for cpu hotplugging)
- Resolves: bz#1361539
  (block/io.c:1342: bdrv_co_do_pwritev: Assertion `!(bs->open_flags & 0x0800)' failed on failed migrate)

* Tue Aug 02 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-18.el7
- kvm-pci-fix-unaligned-access-in-pci_xxx_quad.patch [bz#1343092]
- kvm-msix-make-msix_clr_pending-visible-for-clients.patch [bz#1343092]
- kvm-pci-Introduce-define-for-PM-capability-version-1.1.patch [bz#1343092]
- kvm-pcie-Add-support-for-PCIe-CAP-v1.patch [bz#1343092]
- kvm-pcie-Introduce-function-for-DSN-capability-creation.patch [bz#1343092]
- kvm-vmxnet3-Use-generic-function-for-DSN-capability-defi.patch [bz#1343092]
- kvm-net-Introduce-Toeplitz-hash-calculator.patch [bz#1343092]
- kvm-net-Add-macros-for-MAC-address-tracing.patch [bz#1343092]
- kvm-vmxnet3-Use-common-MAC-address-tracing-macros.patch [bz#1343092]
- kvm-net_pkt-Name-vmxnet3-packet-abstractions-more-generi.patch [bz#1343092]
- kvm-rtl8139-Move-more-TCP-definitions-to-common-header.patch [bz#1343092]
- kvm-net_pkt-Extend-packet-abstraction-as-required-by-e10.patch [bz#1343092]
- kvm-vmxnet3-Use-pci_dma_-API-instead-of-cpu_physical_mem.patch [bz#1343092]
- kvm-e1000_regs-Add-definitions-for-Intel-82574-specific-.patch [bz#1343092]
- kvm-e1000-Move-out-code-that-will-be-reused-in-e1000e.patch [bz#1343092]
- kvm-net-Introduce-e1000e-device-emulation.patch [bz#1343092]
- kvm-e1000e-Fix-build-with-gcc-4.6.3-and-ust-tracing.patch [bz#1343092]
- kvm-pci-fix-pci_requester_id.patch [bz#1350196]
- kvm-hw-pci-delay-bus_master_enable_region-initialization.patch [bz#1350196]
- kvm-q35-allow-dynamic-sysbus.patch [bz#1350196]
- kvm-q35-rhel-allow-dynamic-sysbus.patch [bz#1350196]
- kvm-hw-iommu-enable-iommu-with-device.patch [bz#1350196]
- kvm-machine-remove-iommu-property.patch [bz#1350196]
- kvm-rhel-Revert-unwanted-inconsequential-changes-to-ivsh.patch [bz#1333318]
- kvm-rhel-Disable-ivshmem-plain-migration-ivshmem-doorbel.patch [bz#1333318]
- kvm-nvdimm-fix-memory-leak-in-error-code-path.patch [bz#1361205]
- kvm-i8257-Set-no-user-flag.patch [bz#1337457]
- kvm-bitops-Add-MAKE_64BIT_MASK-macro.patch [bz#1339196]
- kvm-target-i386-Provide-TCG_PHYS_ADDR_BITS.patch [bz#1339196]
- kvm-target-i386-Allow-physical-address-bits-to-be-set.patch [bz#1339196]
- kvm-target-i386-Mask-mtrr-mask-based-on-CPU-physical-add.patch [bz#1339196]
- kvm-target-i386-Fill-high-bits-of-mtrr-mask.patch [bz#1339196]
- kvm-target-i386-Set-physical-address-bits-based-on-host.patch [bz#1339196]
- kvm-target-i386-Enable-host-phys-bits-on-RHEL.patch [bz#1339196]
- kvm-pc-Fix-rhel6.3.0-compat_props-setting.patch [bz#1362264]
- Resolves: bz#1333318
  (ivshmem-plain support in RHEL 7.3)
- Resolves: bz#1337457
  (enable i8257 device)
- Resolves: bz#1339196
  (qemu-kvm (on target host) killed by SIGABRT when migrating a guest from AMD host to Intel host.)
- Resolves: bz#1343092
  (RFE: Integrate e1000e implementation in downstream QEMU)
- Resolves: bz#1350196
  (Enable IOMMU device with -device intel-iommu)
- Resolves: bz#1361205
  (nvdimm: fix memory leak in error code path)
- Resolves: bz#1362264
  (rhel6.3.0 machine-type using wrong compat_props list)

* Fri Jul 29 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-17.el7
- kvm-Disable-mptsas1068-device.patch [bz#1333282]
- kvm-Disable-sd-card.patch [bz#1333282]
- kvm-Disable-rocker-device.patch [bz#1333282]
- kvm-Disable-new-ipmi-devices.patch [bz#1333282]
- kvm-Disable-hyperv-testdev.patch [bz#1333282]
- kvm-Disable-allwiner_ahci-device.patch [bz#1333282]
- kvm-Disable-igd-passthrough-i440FX.patch [bz#1333282]
- kvm-Disable-vfio-platform-device.patch [bz#1333282]
- kvm-tap-vhost-busy-polling-support.patch [bz#1345715 bz#1353791]
- kvm-vl-change-runstate-only-if-new-state-is-different-fr.patch [bz#1355982]
- kvm-virtio-error-out-if-guest-exceeds-virtqueue-size.patch [bz#1359733]
- kvm-migration-set-state-to-post-migrate-on-failure.patch [bz#1355683]
- kvm-block-drop-support-for-using-qcow-2-encryption-with-.patch [bz#1336659]
- kvm-json-streamer-Don-t-leak-tokens-on-incomplete-parse.patch [bz#1360612]
- kvm-json-streamer-fix-double-free-on-exiting-during-a-pa.patch [bz#1360612]
- kvm-Add-dump-guest-memory.py-to-all-archs.patch [bz#1360225]
- Resolves: bz#1333282
  (Disable new devices in QEMU 2.6)
- Resolves: bz#1336659
  (Core dump when re-launch guest with encrypted block device)
- Resolves: bz#1345715
  (Busy polling support for vhost net in qemu)
- Resolves: bz#1353791
  (Busy polling support for vhost)
- Resolves: bz#1355683
  (qemu core dump when do postcopy migration again after canceling a migration in postcopy phase)
- Resolves: bz#1355982
  (qemu will abort after type two"system_reset" after the guest poweroff)
- Resolves: bz#1359733
  (CVE-2016-5403 qemu-kvm-rhev: Qemu: virtio: unbounded memory allocation on host via guest leading to DoS [rhel-7.3])
- Resolves: bz#1360225
  (Can't extract guest memory dump from qemu core)
- Resolves: bz#1360612
  (Memory leak on incomplete JSON parse)

* Tue Jul 26 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-16.el7
- kvm-exec-Remove-cpu-from-cpus-list-during-cpu_exec_exit.patch [bz#1172917]
- kvm-exec-Do-vmstate-unregistration-from-cpu_exec_exit.patch [bz#1172917]
- kvm-cpu-Reclaim-vCPU-objects.patch [bz#1172917]
- kvm-cpu-Add-a-sync-version-of-cpu_remove.patch [bz#1172917]
- kvm-qdev-hotplug-Introduce-HotplugHandler.pre_plug-callb.patch [bz#1172917]
- kvm-cpu-Abstract-CPU-core-type.patch [bz#1172917]
- kvm-xics-xics_kvm-Handle-CPU-unplug-correctly.patch [bz#1172917]
- kvm-spapr_drc-Prevent-detach-racing-against-attach-for-C.patch [bz#1172917]
- kvm-qom-API-to-get-instance_size-of-a-type.patch [bz#1172917]
- kvm-spapr-Abstract-CPU-core-device-and-type-specific-cor.patch [bz#1172917]
- kvm-spapr-Move-spapr_cpu_init-to-spapr_cpu_core.c.patch [bz#1172917]
- kvm-spapr-convert-boot-CPUs-into-CPU-core-devices.patch [bz#1172917]
- kvm-spapr-CPU-hotplug-support.patch [bz#1172917]
- kvm-spapr-CPU-hot-unplug-support.patch [bz#1172917]
- kvm-QMP-Add-query-hotpluggable-cpus.patch [bz#1172917]
- kvm-hmp-Add-info-hotpluggable-cpus-HMP-command.patch [bz#1172917]
- kvm-spapr-implement-query-hotpluggable-cpus-callback.patch [bz#1172917]
- kvm-qapi-Report-support-for-device-cpu-hotplug-in-query-.patch [bz#1172917]
- kvm-qapi-keep-names-in-CpuInstanceProperties-in-sync-wit.patch [bz#1172917]
- kvm-spapr-fix-write-past-end-of-array-error-in-cpu-core-.patch [bz#1172917]
- kvm-spapr-Restore-support-for-older-PowerPC-CPU-cores.patch [bz#1172917]
- kvm-spapr-Restore-support-for-970MP-and-POWER8NVL-CPU-co.patch [bz#1172917]
- kvm-spapr-drop-reference-on-child-object-during-core-rea.patch [bz#1172917]
- kvm-spapr-do-proper-error-propagation-in-spapr_cpu_core_.patch [bz#1172917]
- kvm-spapr-drop-duplicate-variable-in-spapr_core_release.patch [bz#1172917]
- kvm-spapr-Ensure-thread0-of-CPU-core-is-always-realized-.patch [bz#1172917]
- kvm-spapr-fix-core-unplug-crash.patch [bz#1172917]
- kvm-usbredir-add-streams-property.patch [bz#1353180]
- kvm-usbredir-turn-off-streams-for-rhel7.2-older.patch [bz#1353180]
- kvm-net-fix-qemu_announce_self-not-emitting-packets.patch [bz#1343433]
- kvm-Fix-crash-bug-in-rebase-of__com.redhat_drive_add.patch [bz#1352865]
- kvm-ppc-Yet-another-fix-for-the-huge-page-support-detect.patch [bz#1347498]
- kvm-ppc-Huge-page-detection-mechanism-fixes-Episode-III.patch [bz#1347498]
- kvm-hw-ppc-spapr-Make-sure-to-close-the-htab_fd-when-mig.patch [bz#1354341]
- Resolves: bz#1172917
  (add support for CPU hotplugging (qemu-kvm-rhev))
- Resolves: bz#1343433
  (migration: announce_self fix)
- Resolves: bz#1347498
  ([ppc64le] Guest can't boot up with hugepage memdev)
- Resolves: bz#1352865
  (Boot guest with two virtio-scsi-pci devices and spice, QEMU core dump after executing '(qemu)__com.redhat_drive_add')
- Resolves: bz#1353180
  (7.3->7.2 migration: qemu-kvm: usbredirparser: error unserialize caps mismatch)
- Resolves: bz#1354341
  (guest hang after cancel migration then migrate again)

* Fri Jul 22 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-15.el7
- kvm-spapr_pci-Use-correct-DMA-LIOBN-when-composing-the-d.patch [bz#1213667]
- kvm-spapr_iommu-Finish-renaming-vfio_accel-to-need_vfio.patch [bz#1213667]
- kvm-spapr_iommu-Move-table-allocation-to-helpers.patch [bz#1213667]
- kvm-vmstate-Define-VARRAY-with-VMS_ALLOC.patch [bz#1213667]
- kvm-spapr_iommu-Introduce-enabled-state-for-TCE-table.patch [bz#1213667]
- kvm-spapr_iommu-Migrate-full-state.patch [bz#1213667]
- kvm-spapr_iommu-Add-root-memory-region.patch [bz#1213667]
- kvm-spapr_pci-Reset-DMA-config-on-PHB-reset.patch [bz#1213667]
- kvm-spapr_pci-Add-and-export-DMA-resetting-helper.patch [bz#1213667]
- kvm-memory-Add-reporting-of-supported-page-sizes.patch [bz#1213667]
- kvm-spapr-ensure-device-trees-are-always-associated-with.patch [bz#1213667]
- kvm-spapr_iommu-Realloc-guest-visible-TCE-table-when-sta.patch [bz#1213667]
- kvm-vfio-spapr-Add-DMA-memory-preregistering-SPAPR-IOMMU.patch [bz#1213667]
- kvm-vfio-Add-host-side-DMA-window-capabilities.patch [bz#1213667]
- kvm-vfio-spapr-Create-DMA-window-dynamically-SPAPR-IOMMU.patch [bz#1213667]
- kvm-spapr_pci-spapr_pci_vfio-Support-Dynamic-DMA-Windows.patch [bz#1213667]
- kvm-qemu-sockets-use-qapi_free_SocketAddress-in-cleanup.patch [bz#1354090]
- kvm-tap-use-an-exit-notifier-to-call-down_script.patch [bz#1354090]
- kvm-slirp-use-exit-notifier-for-slirp_smb_cleanup.patch [bz#1354090]
- kvm-net-do-not-use-atexit-for-cleanup.patch [bz#1354090]
- kvm-virtio-mmio-format-transport-base-address-in-BusClas.patch [bz#1356815]
- kvm-vfio-pci-Hide-ARI-capability.patch [bz#1356376]
- kvm-qxl-factor-out-qxl_get_check_slot_offset.patch [bz#1235732]
- kvm-qxl-store-memory-region-and-offset-instead-of-pointe.patch [bz#1235732]
- kvm-qxl-fix-surface-migration.patch [bz#1235732]
- kvm-qxl-fix-qxl_set_dirty-call-in-qxl_dirty_one_surface.patch [bz#1235732]
- kvm-Add-install-dependency-required-for-usb-streams.patch [bz#1354443]
- Resolves: bz#1213667
  (Dynamic DMA Windows for VFIO on Power (qemu component))
- Resolves: bz#1235732
  (spice-gtk shows outdated screen state after migration [qemu-kvm-rhev])
- Resolves: bz#1354090
  (Boot guest with vhostuser server mode, QEMU prompt 'Segmentation fault' after executing '(qemu)system_powerdown')
- Resolves: bz#1354443
  (/usr/libexec/qemu-kvm: undefined symbol: libusb_free_ss_endpoint_companion_descriptor)
- Resolves: bz#1356376
  ([Q35] Nic which passthrough from host didn't be found in guest when enable multifunction)
- Resolves: bz#1356815
  (AArch64: backport virtio-mmio dev pathname fix)

* Tue Jul 19 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-14.el7
- kvm-add-vgabios-virtio.bin-symlink.patch [bz#1347402]
- kvm-usb-enable-streams-support.patch [bz#1033733]
- kvm-hw-arm-virt-kill-7.2-machine-type.patch [bz#1356814]
- kvm-blockdev-Fix-regression-with-the-default-naming-of-t.patch [bz#1353801]
- kvm-qemu-iotests-Test-naming-of-throttling-groups.patch [bz#1353801]
- kvm-target-i386-Show-host-and-VM-TSC-frequencies-on-mism.patch [bz#1351442]
- Resolves: bz#1033733
  (RFE: add support for USB-3 bulk streams - qemu-kvm)
- Resolves: bz#1347402
  (vgabios-virtio.bin should be symlinked in qemu-kvm-rhev)
- Resolves: bz#1351442
  ("TSC frequency mismatch" warning message after migration)
- Resolves: bz#1353801
  (The default io throttling group name is null, which makes all throttled disks with a default group name in the same group)
- Resolves: bz#1356814
  (AArch64: remove non-released 7.2 machine type)

* Tue Jul 12 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-13.el7
- kvm-block-gluster-add-support-for-selecting-debug-loggin.patch [bz#1320714]
- kvm-Revert-static-checker-e1000-82540em-got-aliased-to-e.patch [bz#1353070]
- kvm-Revert-e1000-use-alias-for-default-model.patch [bz#1353070]
- kvm-7.x-compat-e1000-82540em.patch [bz#1353070]
- kvm-target-i386-add-Skylake-Client-cpu-model.patch [bz#1327589]
- kvm-scsi-generic-Merge-block-max-xfer-len-in-INQUIRY-res.patch [bz#1353816]
- kvm-raw-posix-Fetch-max-sectors-for-host-block-device.patch [bz#1353816]
- kvm-scsi-Advertise-limits-by-blocksize-not-512.patch [bz#1353816]
- kvm-mirror-clarify-mirror_do_read-return-code.patch [bz#1336705]
- kvm-mirror-limit-niov-to-IOV_MAX-elements-again.patch [bz#1336705]
- kvm-iotests-add-small-granularity-mirror-test.patch [bz#1336705]
- Resolves: bz#1320714
  ([RFE] Allow the libgfapi logging level to be controlled.)
- Resolves: bz#1327589
  (Add Skylake CPU model)
- Resolves: bz#1336705
  (Drive mirror with option granularity fail)
- Resolves: bz#1353070
  (Migration is failed from host RHEL7.2.z to host RHEL7.3 with "-M rhel6.6.0 -device e1000-82540em")
- Resolves: bz#1353816
  (expose host BLKSECTGET limit in scsi-block (qemu-kvm-rhev))

* Fri Jul 08 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-12.el7
- kvm-Fix-crash-with-__com.redhat_drive_del.patch [bz#1341531]
- kvm-hw-arm-virt-fix-limit-of-64-bit-ACPI-ECAM-PCI-MMIO-r.patch [bz#1349337]
- kvm-Increase-locked-memory-limit-for-all-users-not-just-.patch [bz#1350735]
- kvm-target-i386-Remove-SSE4a-from-qemu64-CPU-model.patch [bz#1318386 bz#1321139 bz#1321139]
- kvm-target-i386-Remove-ABM-from-qemu64-CPU-model.patch [bz#1318386 bz#1321139 bz#1321139]
- kvm-pc-Recover-PC_RHEL7_1_COMPAT-from-RHEL-7.2-code.patch [bz#1318386 bz#1318386 bz#1321139]
- kvm-pc-Include-missing-PC_COMPAT_2_3-entries-in-PC_RHEL7.patch [bz#1318386 bz#1318386 bz#1321139]
- kvm-vhost-user-disable-chardev-handlers-on-close.patch [bz#1347077]
- kvm-char-clean-up-remaining-chardevs-when-leaving.patch [bz#1347077]
- kvm-socket-add-listen-feature.patch [bz#1347077]
- kvm-socket-unlink-unix-socket-on-remove.patch [bz#1347077]
- kvm-char-do-not-use-atexit-cleanup-handler.patch [bz#1347077]
- kvm-vfio-add-pcie-extended-capability-support.patch [bz#1346688]
- kvm-vfio-pci-Hide-SR-IOV-capability.patch [bz#1346688]
- kvm-memory-Add-MemoryRegionIOMMUOps.notify_started-stopp.patch [bz#1346920]
- kvm-intel_iommu-Throw-hw_error-on-notify_started.patch [bz#1346920]
- Resolves: bz#1318386
  (pc-rhel7.2.0 machine type definition needs some fixes)
- Resolves: bz#1321139
  (qemu-kvm-rhev prints warnings in the default CPU+machine-type configuration.)
- Resolves: bz#1341531
  (qemu gets SIGSEGV when hot-plug a scsi hostdev device with duplicate target address)
- Resolves: bz#1346688
  ([Q35] vfio read-only SR-IOV capability confuses OVMF)
- Resolves: bz#1346920
  (vIOMMU: prevent unsupported configurations with vfio)
- Resolves: bz#1347077
  (vhost-user: A socket file is not deleted after VM's port is detached.)
- Resolves: bz#1349337
  (hw/arm/virt: fix limit of 64-bit ACPI/ECAM PCI MMIO range)
- Resolves: bz#1350735
  (memory locking limit for regular users is too low to launch guests through libvirt)

* Fri Jul 01 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-11.el7
- kvm-Postcopy-Avoid-0-length-discards.patch [bz#1347256]
- kvm-Migration-Split-out-ram-part-of-qmp_query_migrate.patch [bz#1347256]
- kvm-Postcopy-Add-stats-on-page-requests.patch [bz#1347256]
- kvm-test-Postcopy.patch [bz#1347256]
- kvm-tests-fix-libqtest-socket-timeouts.patch [bz#1347256]
- kvm-Postcopy-Check-for-support-when-setting-the-capabili.patch [bz#1347256]
- kvm-rbd-change-error_setg-to-error_setg_errno.patch [bz#1329641]
- kvm-ppc-Disable-huge-page-support-if-it-is-not-available.patch [bz#1347498]
- kvm-acpi-do-not-use-TARGET_PAGE_SIZE.patch [bz#1270345]
- kvm-acpi-convert-linker-from-GArray-to-BIOSLinker-struct.patch [bz#1270345]
- kvm-acpi-simplify-bios_linker-API-by-removing-redundant-.patch [bz#1270345]
- kvm-acpi-cleanup-bios_linker_loader_cleanup.patch [bz#1270345]
- kvm-tpm-apci-cleanup-TCPA-table-initialization.patch [bz#1270345]
- kvm-acpi-make-bios_linker_loader_add_pointer-API-offset-.patch [bz#1270345]
- kvm-acpi-make-bios_linker_loader_add_checksum-API-offset.patch [bz#1270345]
- kvm-pc-dimm-get-memory-region-from-get_memory_region.patch [bz#1270345]
- kvm-pc-dimm-introduce-realize-callback.patch [bz#1270345]
- kvm-pc-dimm-introduce-get_vmstate_memory_region-callback.patch [bz#1270345]
- kvm-nvdimm-support-nvdimm-label.patch [bz#1270345]
- kvm-acpi-add-aml_object_type.patch [bz#1270345]
- kvm-acpi-add-aml_call5.patch [bz#1270345]
- kvm-nvdimm-acpi-set-HDLE-properly.patch [bz#1270345]
- kvm-nvdimm-acpi-save-arg3-of-_DSM-method.patch [bz#1270345]
- kvm-nvdimm-acpi-check-UUID.patch [bz#1270345]
- kvm-nvdimm-acpi-abstract-the-operations-for-root-nvdimm-.patch [bz#1270345]
- kvm-nvdimm-acpi-check-revision.patch [bz#1270345]
- kvm-nvdimm-acpi-support-Get-Namespace-Label-Size-functio.patch [bz#1270345]
- kvm-nvdimm-acpi-support-Get-Namespace-Label-Data-functio.patch [bz#1270345]
- kvm-nvdimm-acpi-support-Set-Namespace-Label-Data-functio.patch [bz#1270345]
- kvm-docs-add-NVDIMM-ACPI-documentation.patch [bz#1270345]
- kvm-Fix-qemu-kvm-does-not-quit-when-booting-guest-w-241-.patch [bz#1126666]
- kvm-Adjust-locked-memory-limits-to-allow-unprivileged-VM.patch [bz#1350735]
- kvm-dma-helpers-dma_blk_io-cancel-support.patch [bz#1346237]
- Resolves: bz#1126666
  (qemu-kvm does not quit when booting guest w/ 161 vcpus and "-no-kvm")
- Resolves: bz#1270345
  ([Intel 7.3 FEAT] Virtualization support for NVDIMM - qemu support)
- Resolves: bz#1329641
  ([RFE]Ceph/RBD block driver for qemu-kvm : change error_setg() to error_setg_errno())
- Resolves: bz#1346237
  (win 10.x86_64 guest coredump when execute avocado test case: win_virtio_update.install_driver)
- Resolves: bz#1347256
  (Backport 2.7 postcopy fix, test and stats)
- Resolves: bz#1347498
  ([ppc64le] Guest can't boot up with hugepage memdev)
- Resolves: bz#1350735
  (memory locking limit for regular users is too low to launch guests through libvirt)

* Tue Jun 28 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-10.el7
- kvm-block-clarify-error-message-for-qmp-eject.patch [bz#961589]
- kvm-blockdev-clean-up-error-handling-in-do_open_tray.patch [bz#961589]
- kvm-blockdev-clarify-error-on-attempt-to-open-locked-tra.patch [bz#961589]
- kvm-blockdev-backup-Use-bdrv_lookup_bs-on-target.patch [bz#1336310 bz#1339498]
- kvm-blockdev-backup-Don-t-move-target-AioContext-if-it-s.patch [bz#1336310 bz#1339498]
- kvm-virtio-blk-Remove-op-blocker-for-dataplane.patch [bz#1336310 bz#1339498]
- kvm-virtio-scsi-Remove-op-blocker-for-dataplane.patch [bz#1336310 bz#1339498]
- kvm-spec-add-a-sample-kvm.conf-to-enable-Nested-Virtuali.patch [bz#1290150]
- Resolves: bz#1290150
  (Include example kvm.conf with nested options commented out)
- Resolves: bz#1336310
  (virtio-scsi data-plane does not support block management QMP commands)
- Resolves: bz#1339498
  (Core dump when do 'block-job-complete' after 'drive-mirror')
- Resolves: bz#961589
  (rhel7 guest sometimes didnt unlock the cdrom when qemu-kvm trying to eject)

* Thu Jun 23 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-9.el7
- kvm-7.2-machine-type-compatibility.patch [bz#1344269]
- kvm-vhost-user-add-ability-to-know-vhost-user-backend-di.patch [bz#1322087]
- kvm-tests-vhost-user-bridge-add-client-mode.patch [bz#1322087]
- kvm-tests-vhost-user-bridge-workaround-stale-vring-base.patch [bz#1322087]
- kvm-qemu-char-add-qemu_chr_disconnect-to-close-a-fd-acce.patch [bz#1322087]
- kvm-vhost-user-disconnect-on-start-failure.patch [bz#1322087]
- kvm-vhost-net-do-not-crash-if-backend-is-not-present.patch [bz#1322087]
- kvm-vhost-net-save-restore-vhost-user-acked-features.patch [bz#1322087]
- kvm-vhost-net-save-restore-vring-enable-state.patch [bz#1322087]
- kvm-tests-append-i386-tests.patch [bz#1322087]
- kvm-test-start-vhost-user-reconnect-test.patch [bz#1322087]
- kvm-block-Prevent-sleeping-jobs-from-resuming-if-they-ha.patch [bz#1265179]
- kvm-blockjob-move-iostatus-reset-out-of-block_job_enter.patch [bz#1265179]
- kvm-blockjob-rename-block_job_is_paused.patch [bz#1265179]
- kvm-blockjob-add-pause-points.patch [bz#1265179]
- kvm-blockjob-add-block_job_get_aio_context.patch [bz#1265179]
- kvm-block-use-safe-iteration-over-AioContext-notifiers.patch [bz#1265179]
- kvm-blockjob-add-AioContext-attached-callback.patch [bz#1265179]
- kvm-mirror-follow-AioContext-change-gracefully.patch [bz#1265179]
- kvm-backup-follow-AioContext-change-gracefully.patch [bz#1265179]
- kvm-block-Fix-snapshot-on-with-aio-native.patch [bz#1336649]
- kvm-block-iscsi-avoid-potential-overflow-of-acb-task-cdb.patch [bz#1340930]
- kvm-block-fixed-BdrvTrackedRequest-filling-in-bdrv_co_di.patch [bz#1348763]
- kvm-block-fix-race-in-bdrv_co_discard-with-drive-mirror.patch [bz#1348763]
- kvm-block-process-before_write_notifiers-in-bdrv_co_disc.patch [bz#1348763]
- Resolves: bz#1265179
  (With dataplane, when migrate to  remote NBD disk after drive-mirror, qemu core dump ( both src host and des host))
- Resolves: bz#1322087
  (No recovery after vhost-user process restart)
- Resolves: bz#1336649
  ([RHEL.7.3] Guest will not boot up when specify aio=native and snapshot=on together)
- Resolves: bz#1340930
  (CVE-2016-5126 qemu-kvm-rhev: Qemu: block: iscsi: buffer overflow in iscsi_aio_ioctl [rhel-7.3])
- Resolves: bz#1344269
  (Migration: Fixup machine types and HW_COMPAT (stage 2a))
- Resolves: bz#1348763
  (Fix dirty marking with block discard requests)

* Tue Jun 21 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-8.el7
- kvm-Disable-Windows-enlightnements.patch [bz#1336517]
- kvm-ppc-spapr-Refactor-h_client_architecture_support-CPU.patch [bz#1341492]
- kvm-ppc-Split-pcr_mask-settings-into-supported-bits-and-.patch [bz#1341492]
- kvm-ppc-Provide-function-to-get-CPU-class-of-the-host-CP.patch [bz#1341492]
- kvm-ppc-Improve-PCR-bit-selection-in-ppc_set_compat.patch [bz#1341492]
- kvm-ppc-Add-PowerISA-2.07-compatibility-mode.patch [bz#1341492]
- kvm-machine-types-fix-pc_machine_-_options-chain.patch [bz#1344320]
- kvm-Fix-rhel6-rom-file.patch [bz#1344320]
- kvm-fix-vga-type-for-older-machines.patch [bz#1344320]
- kvm-Revert-aio_notify-force-main-loop-wakeup-with-SIGIO-.patch [bz#1188656]
- kvm-Make-avx2-configure-test-work-with-O2.patch [bz#1323294]
- kvm-avx2-configure-Use-primitives-in-test.patch [bz#1323294]
- kvm-vfio-Fix-broken-EEH.patch [bz#1346627]
- Resolves: bz#1188656
  (lost block IO completion notification (for virtio-scsi disk) hangs main loop)
- Resolves: bz#1323294
  (AVX-2 migration optimisation)
- Resolves: bz#1336517
  (Disable hv-vpindex, hv-runtime, hv-reset, hv-synic & hv-stimer enlightenment for Windows)
- Resolves: bz#1341492
  (QEMU on POWER does not support the PowerISA 2.07 compatibility mode)
- Resolves: bz#1344320
  (migration: fix pc_i440fx_*_options chaining)
- Resolves: bz#1346627
  (qemu discards EEH ioctl results)

* Thu Jun 16 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-7.el7
- kvm-pc-allow-raising-low-memory-via-max-ram-below-4g-opt.patch [bz#1176144]
- kvm-vga-add-sr_vbe-register-set.patch [bz#1331415 bz#1346976]
- Resolves: bz#1176144
  ([Nokia RHEL 7.3 Feature]: 32-bit operating systems get very little memory space with new Qemu's)
- Resolves: bz#1331415
  (CVE-2016-3710 qemu-kvm-rhev: qemu: incorrect banked access bounds checking in vga module [rhel-7.3])
- Resolves: bz#1346976
  (Regression from CVE-2016-3712: windows installer fails to start)
- Resolves: bz#1339467
  (User can not create windows 7 virtual machine in rhevm3.6.5.)

* Wed Jun 15 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-6.el7
- kvm-throttle-refuse-iops-size-without-iops-total-read-wr.patch [bz#1342330]
- kvm-scsi-mark-TYPE_SCSI_DISK_BASE-as-abstract.patch [bz#1338043]
- kvm-scsi-disk-add-missing-break.patch [bz#1338043]
- kvm-Disable-spapr-rng.patch [bz#1343891]
- kvm-spec-Update-rules-before-triggering-for-kvm-device.patch [bz#1338755]
- kvm-spec-Do-not-package-ivshmem-server-and-ivshmem-clien.patch [bz#1320476]
- Resolves: bz#1320476
  (Failed to upgrade qemu-kvm-tools-rhev from 2.3.0 to 2.5.0)
- Resolves: bz#1338043
  (scsi-block fix - receive the right SCSI status on reads and writes)
- Resolves: bz#1338755
  (qemu-kvm-rhev doesn't reload udev rules before triggering for kvm device)
- Resolves: bz#1342330
  (There is no error prompt when set the io throttling parameters iops_size without iops)
- Resolves: bz#1343891
  (Disable spapr-rng device in downstream qemu 2.6)

* Mon Jun 06 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-5.el7
- kvm-spapr-update-RHEL-7.2-machine-type.patch [bz#1316303]
- kvm-migration-fix-HW_COMPAT_RHEL7_2.patch [bz#1316303]
- kvm-target-i386-add-a-generic-x86-nmi-handler.patch [bz#1335720]
- kvm-nmi-remove-x86-specific-nmi-handling.patch [bz#1335720]
- kvm-cpus-call-the-core-nmi-injection-function.patch [bz#1335720]
- kvm-spec-link-sgabios.bin-only-for-x86_64.patch [bz#1337917]
- kvm-Add-PCIe-bridge-devices-for-AArch64.patch [bz#1326420]
- kvm-Remove-unsupported-VFIO-devices-from-QEMU.patch [bz#1326420]
- kvm-hw-net-spapr_llan-Delay-flushing-of-the-RX-queue-whi.patch [bz#1210221]
- kvm-hw-net-spapr_llan-Provide-counter-with-dropped-rx-fr.patch [bz#1210221]
- kvm-iscsi-pass-SCSI-status-back-for-SG_IO.patch [bz#1338043]
- kvm-dma-helpers-change-BlockBackend-to-opaque-value-in-D.patch [bz#1338043]
- kvm-scsi-disk-introduce-a-common-base-class.patch [bz#1338043]
- kvm-scsi-disk-introduce-dma_readv-and-dma_writev.patch [bz#1338043]
- kvm-scsi-disk-add-need_fua_emulation-to-SCSIDiskClass.patch [bz#1338043]
- kvm-scsi-disk-introduce-scsi_disk_req_check_error.patch [bz#1338043]
- kvm-scsi-block-always-use-SG_IO.patch [bz#1338043]
- kvm-tools-kvm_stat-Powerpc-related-fixes.patch [bz#1337033]
- kvm-pc-New-default-pc-i440fx-rhel7.3.0-machine-type.patch [bz#1305121]
- kvm-7.3-mismerge-fix-Fix-ich9-intel-hda-compatibility.patch [bz#1342015]
- kvm-PC-migration-compat-Section-footers-global-state.patch [bz#1342015]
- kvm-fw_cfg-for-7.2-compatibility.patch [bz#1342015]
- kvm-pc-Create-new-pc-q35-rhel7.3.0-machine-type.patch [bz#1342015]
- kvm-q35-Remove-7.0-7.1-7.2-machine-types.patch [bz#1342015]
- Resolves: bz#1210221
  (Netperf UDP_STREAM Lost most of the packets on spapr-vlan device)
- Resolves: bz#1305121
  (rhel7.3.0 machine-types)
- Resolves: bz#1316303
  (Live migration of VMs from RHEL 7.2 <--> 7.3 with pseries-rhel7.2.0 machine type (qemu 2.6))
- Resolves: bz#1326420
  (AArch64: clean and add devices to fully support aarch64 vm)
- Resolves: bz#1335720
  (watchdog action 'inject-nmi' takes no effect)
- Resolves: bz#1337033
  (kvm_stat AttributeError: 'ArchPPC' object has no attribute 'exit_reasons')
- Resolves: bz#1337917
  (qemu-kvm-rhev: Only ship /usr/share/qemu-kvm/sgabios.bin on x86)
- Resolves: bz#1338043
  (scsi-block fix - receive the right SCSI status on reads and writes)
- Resolves: bz#1342015
  (Migration: Fixup machine types and HW_COMPAT (stage 1b))

* Wed May 25 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-4.el7
- kvm-pc-Use-right-HW_COMPAT_-macros-at-PC_RHEL7-compat-ma.patch [bz#1318386]
- kvm-compat-Add-missing-any_layout-in-HW_COMPAT_RHEL7_1.patch [bz#1318386]
- kvm-RHEL-Disable-unsupported-PowerPC-CPU-models.patch [bz#1317977]
- kvm-spec-Use-correct-upstream-QEMU-version.patch [bz#1335705]
- Resolves: bz#1317977
  (qemu-kvm-rhev supports a lot of CPU models)
- Resolves: bz#1318386
  (pc-rhel7.2.0 machine type definition needs some fixes)
- Resolves: bz#1335705
  ('QEMU 2.5.94 monitor' is used for qemu-kvm-rhev-2.6.0-1.el7.x86_64)

* Mon May 23 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-3.el7
- kvm-qmp-Report-drive_add-error-to-monitor.patch [bz#1337100]
- kvm-spec-Remove-dependency-to-ipxe-roms-qemu-for-aarch64.patch [bz#1337496]
- Resolves: bz#1337100
  (redhat_drive_add should report error to qmp if it fails to initialize)
- Resolves: bz#1337496
  (qemu-kvm-rhev should not depend on ipxe-roms-qemu on aarch64)

* Tue May 17 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-2.el7
- kvm-Fix-SLOF-dependency.patch [bz#1336296]
- Resolves: bz#1336296
  (failed dependencies on SLOF)

* Thu May 12 2016 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.6.0-1.el7
- Rebase to QEMU 2.6.0 [bz#1289417]
- Resolves: bz#1289417
  (Rebase to QEMU 2.6)

* Wed Oct 14 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-31.el7
- kvm-Migration-Generate-the-completed-event-only-when-we-.patch [bz#1271145]
- Resolves: bz#1271145
  (Guest OS paused after migration.)

* Mon Oct 12 2015 Jeff E. Nelson <jen@redhat.com> - rhev-2.3.0-30.el7
- kvm-memhp-extend-address-auto-assignment-to-support-gaps.patch [bz#1267533]
- kvm-pc-memhp-force-gaps-between-DIMM-s-GPA.patch [bz#1267533]
- kvm-memory-allow-destroying-a-non-empty-MemoryRegion.patch [bz#1264347]
- kvm-hw-do-not-pass-NULL-to-memory_region_init-from-insta.patch [bz#1264347]
- kvm-tests-Fix-how-qom-test-is-run.patch [bz#1264347]
- kvm-libqtest-Clean-up-unused-QTestState-member-sigact_ol.patch [bz#1264347]
- kvm-libqtest-New-hmp-friends.patch [bz#1264347]
- kvm-device-introspect-test-New-covering-device-introspec.patch [bz#1264347]
- kvm-qmp-Fix-device-list-properties-not-to-crash-for-abst.patch [bz#1264347]
- kvm-qdev-Protect-device-list-properties-against-broken-d.patch [bz#1264347]
- kvm-Revert-qdev-Use-qdev_get_device_class-for-device-typ.patch [bz#1264347]
- Resolves: bz#1264347
  (QMP device-list-properties crashes for CPU devices)
- Resolves: bz#1267533
  (qemu quit when rebooting guest which hotplug memory >=13 times)

* Thu Oct 08 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-29.el7
- kvm-vfio-Remove-unneeded-union-from-VFIOContainer.patch [bz#1259556]
- kvm-vfio-Generalize-vfio_listener_region_add-failure-pat.patch [bz#1259556]
- kvm-vfio-Check-guest-IOVA-ranges-against-host-IOMMU-capa.patch [bz#1259556]
- kvm-vfio-Record-host-IOMMU-s-available-IO-page-sizes.patch [bz#1259556]
- kvm-memory-Allow-replay-of-IOMMU-mapping-notifications.patch [bz#1259556]
- kvm-vfio-Allow-hotplug-of-containers-onto-existing-guest.patch [bz#1259556]
- kvm-spapr_pci-Allow-PCI-host-bridge-DMA-window-to-be-con.patch [bz#1259556]
- kvm-spapr_iommu-Rename-vfio_accel-parameter.patch [bz#1259556]
- kvm-spapr_iommu-Provide-a-function-to-switch-a-TCE-table.patch [bz#1259556]
- kvm-spapr_pci-Allow-VFIO-devices-to-work-on-the-normal-P.patch [bz#1259556]
- Resolves: bz#1259556
  (Allow VFIO devices on the same guest PHB as emulated devices)

* Mon Oct 05 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-28.el7
- kvm-rhel-Revert-unwanted-cannot_instantiate_with_device_.patch [bz#1224542]
- kvm-Disable-additional-e1000-models.patch [bz#1224542 bz#1265161]
- kvm-Remove-intel-iommu-device.patch [bz#1224542]
- kvm-virtio-net-unbreak-self-announcement-and-guest-offlo.patch [bz#1262232]
- kvm-block-mirror-fix-full-sync-mode-when-target-does-not.patch [bz#1136382]
- Resolves: bz#1136382
  (block: Mirroring to raw block device doesn't zero out unused blocks)
- Resolves: bz#1224542
  (unsupported devices need to be disabled in qemu-kvm-rhev after rebasing to 2.3.0)
- Resolves: bz#1262232
  (self announcement and ctrl offloads does not work after migration)
- Resolves: bz#1265161
  (Support various e1000 variants)

* Wed Sep 30 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-27.el7
- kvm-sdl2-Fix-RGB555.patch [bz#1247479]
- kvm-spice-surface-switch-fast-path-requires-same-format-.patch [bz#1247479]
- kvm-virtio-blk-only-clear-VIRTIO_F_ANY_LAYOUT-for-legacy.patch [bz#1207687]
- kvm-vhost-enable-vhost-without-without-MSI-X.patch [bz#1207687]
- kvm-vhost-user-Send-VHOST_RESET_OWNER-on-vhost-stop.patch [bz#1207687]
- kvm-virtio-avoid-leading-underscores-for-helpers.patch [bz#1207687]
- kvm-vhost-user-use-VHOST_USER_XXX-macro-for-switch-state.patch [bz#1207687]
- kvm-vhost-user-add-protocol-feature-negotiation.patch [bz#1207687]
- kvm-vhost-rename-VHOST_RESET_OWNER-to-VHOST_RESET_DEVICE.patch [bz#1207687]
- kvm-vhost-user-add-VHOST_USER_GET_QUEUE_NUM-message.patch [bz#1207687]
- kvm-vhost-introduce-vhost_backend_get_vq_index-method.patch [bz#1207687]
- kvm-vhost-user-add-multiple-queue-support.patch [bz#1207687]
- kvm-vhost-user-add-a-new-message-to-disable-enable-a-spe.patch [bz#1207687]
- Resolves: bz#1207687
  ([6wind 7.2 FEAT]: vhost-user does not support multique)
- Resolves: bz#1247479
  (display mess when boot a win2012-r2-64 guest with -vga std)

* Thu Sep 24 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-26.el7
- kvm-qcow2-Make-size_to_clusters-return-uint64_t.patch [bz#1260365]
- kvm-iotests-Add-test-for-checking-large-image-files.patch [bz#1260365]
- Resolves: bz#1260365
  (Guest image created coredump after installation.)

* Wed Sep 23 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-25.el7
- kvm-block-backend-Expose-bdrv_write_zeroes.patch [bz#1256541]
- kvm-qemu-img-convert-Rewrite-copying-logic.patch [bz#1256541]
- kvm-main-loop-fix-qemu_notify_event-for-aio_notify-optim.patch [bz#1256541]
- kvm-error-New-error_fatal.patch [bz#1232308]
- kvm-Fix-bad-error-handling-after-memory_region_init_ram.patch [bz#1232308]
- kvm-loader-Fix-memory_region_init_resizeable_ram-error-h.patch [bz#1232308]
- kvm-memory-Fix-bad-error-handling-in-memory_region_init_.patch [bz#1232308]
- kvm-spapr_pci-encode-class-code-including-Prog-IF-regist.patch [bz#1264845]
- kvm-scripts-dump-guest-memory.py-fix-after-RAMBlock-chan.patch [bz#1234802]
- kvm-spec-Require-proper-version-of-SLOF.patch [bz#1263795]
- Resolves: bz#1232308
  ([abrt] qemu-system-x86: qemu_ram_alloc(): qemu-system-x86_64 killed by SIGABRT)
- Resolves: bz#1234802
  ([RHEL7.2] dump-guest-memory failed because of Python Exception <class 'gdb.error'> There is no member named length.)
- Resolves: bz#1256541
  (qemu-img hangs forever in aio_poll when used to convert some images)
- Resolves: bz#1263795
  (vfio device can't be hot unplugged on powerpc guest)
- Resolves: bz#1264845
  ([regression] Guest usb mouse/keyboard could not be used on qemu-kvm-rhev-2.3.0-24.el7.ppc64le)

* Fri Sep 18 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-24.el7
- kvm-spapr-Don-t-use-QOM-syntax-for-DR-connectors.patch [bz#1262143]
- kvm-virtio-mmio-ioeventfd-support.patch [bz#1185480]
- kvm-scsi-fix-buffer-overflow-in-scsi_req_parse_cdb-CVE-2.patch [bz#1244334]
- kvm-spapr-Populate-ibm-associativity-lookup-arrays-corre.patch [bz#1262670]
- kvm-ppc-spapr-Fix-buffer-overflow-in-spapr_populate_drco.patch [bz#1262670]
- kvm-spapr_pci-Introduce-a-liobn-number-generating-macros.patch [bz#1263795]
- kvm-spapr_iommu-Make-spapr_tce_find_by_liobn-public.patch [bz#1263795]
- kvm-spapr_pci-Rework-device-tree-rendering.patch [bz#1263795]
- kvm-spapr_pci-enumerate-and-add-PCI-device-tree.patch [bz#1263795]
- kvm-spapr_pci-populate-ibm-loc-code.patch [bz#1263795]
- kvm-tests-remove-irrelevant-assertions-from-test-aio.patch [bz#1211689]
- kvm-aio-posix-move-pollfds-to-thread-local-storage.patch [bz#1211689]
- kvm-aio-Introduce-type-in-aio_set_fd_handler-and-aio_set.patch [bz#1211689]
- kvm-aio-Save-type-to-AioHandler.patch [bz#1211689]
- kvm-aio-posix-Introduce-aio_poll_clients.patch [bz#1211689]
- kvm-block-Mark-fd-handlers-as-protocol.patch [bz#1211689]
- kvm-nbd-Mark-fd-handlers-client-type-as-nbd-server.patch [bz#1211689]
- kvm-aio-Mark-ctx-notifier-s-client-type-as-context.patch [bz#1211689]
- kvm-dataplane-Mark-host-notifiers-client-type-as-datapla.patch [bz#1211689]
- kvm-block-Introduce-bdrv_aio_poll.patch [bz#1211689]
- kvm-block-Replace-nested-aio_poll-with-bdrv_aio_poll.patch [bz#1211689]
- kvm-block-Only-poll-block-layer-fds-in-bdrv_aio_poll.patch [bz#1211689]
- Resolves: bz#1185480
  (backport ioeventfd support for virtio-mmio)
- Resolves: bz#1211689
  (atomic live snapshots are not atomic with dataplane-backed devices)
- Resolves: bz#1244334
  (qemu-kvm-rhev: Qemu: scsi stack buffer overflow [rhel-7.2])
- Resolves: bz#1262143
  (VM startup is very slow with large amounts of hotpluggable memory)
- Resolves: bz#1262670
  ([PowerKVM]SIGSEGV when boot up guest with -numa node and set up the cpus in one node to the boundary)
- Resolves: bz#1263795
  (vfio device can't be hot unplugged on powerpc guest)

* Tue Sep 15 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-23.el7
- kvm-scsi-disk-Fix-assertion-failure-on-WRITE-SAME.patch [bz#1247042]
- kvm-mirror-Speed-up-bitmap-initial-scanning.patch [bz#1259229]
- kvm-qemu-iotests-Disable-099-requires-blkverify.patch [bz#1257059]
- kvm-spapr-Reduce-advertised-max-LUNs-for-spapr_vscsi.patch [bz#1260464]
- kvm-vnc-Don-t-assert-if-opening-unix-socket-fails.patch [bz#1261263]
- kvm-qcow2-Handle-EAGAIN-returned-from-update_refcount.patch [bz#1254927]
- kvm-pc-memhotplug-fix-incorrectly-set-reserved-memory-en.patch [bz#1261846]
- kvm-pc-memhotplug-keep-reserved-memory-end-broken-on-rhe.patch [bz#1261846]
- Resolves: bz#1247042
  (qemu quit when using sg_write_same command inside RHEL7.2 guest)
- Resolves: bz#1254927
  (qemu-img shows Input/output error when compressing guest image)
- Resolves: bz#1257059
  (qemu-iotests 099 failed for vmdk)
- Resolves: bz#1259229
  (drive-mirror blocks QEMU due to lseek64() on raw image files)
- Resolves: bz#1260464
  (The spapr vscsi disks for lun id '9-31' and channel id '4-7' could not be recognized inside a power pc guest)
- Resolves: bz#1261263
  (qemu crash while start a guest with invalid vnc socket path)
- Resolves: bz#1261846
  (qemu-kvm-rhev: 64-bit PCI bars may overlap hotplugged memory and vice verse)

* Thu Sep 03 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-22.el7
- kvm-mirror-Fix-coroutine-reentrance.patch [bz#1251487]
- kvm-RHEL-Set-vcpus-hard-limit-to-240-for-Power.patch [bz#1257781]
- kvm-provide-vhost-module-config-file-with-max_mem_region.patch [bz#1255349]
- Resolves: bz#1251487
  (qemu core dump when do drive mirror)
- Resolves: bz#1255349
  (vhost: default value of 'max_mem_regions' should be set  larger(>=260) than 64)
- Resolves: bz#1257781
  (The prompt is confusing when boot a guest with larger vcpu number than host physical cpu)

* Fri Aug 28 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-21.el7
- kvm-vnc-fix-memory-corruption-CVE-2015-5225.patch [bz#1255898]
- Resolves: bz#1255898
  (CVE-2015-5225 qemu-kvm-rhev: Qemu: ui: vnc: heap memory corruption in vnc_refresh_server_surface [rhel-7.2])

* Thu Aug 27 2015 Yash Mankad <ymankad@redhat.com> - rhev-2.3.0-20.el7 
- kvm-pseries-define-coldplugged-devices-as-configured.patch [bz#1243721]
- kvm-spice-fix-spice_chr_add_watch-pre-condition.patch [bz#1128992]
- Resolves: bz#1128992
  (Spiceport character device is not reliable caused domain shutoff)
- Resolves: bz#1243721
  (After hotunpug virtio device, the device still exist in pci info)

* Mon Aug 24 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-19.el7
- kvm-ppc-add-helpful-message-when-KVM-fails-to-start-VCPU.patch [bz#1215618]
- kvm-pci-allow-0-address-for-PCI-IO-MEM-regions.patch [bz#1241886]
- kvm-RHEL-Suppress-scary-but-unimportant-errors-for-KVM-V.patch [bz#1237034]
- Resolves: bz#1215618
  (Unhelpful error message on Power when SMT is enabled)
- Resolves: bz#1237034
  (Error prompt while booting with vfio-pci device)
- Resolves: bz#1241886
  (hot plugged pci devices won't appear unless reboot)

* Fri Aug 14 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-18.el7
- kvm-vhost-correctly-pass-error-to-caller-in-vhost_dev_en.patch [bz#1248312]
- kvm-Revert-virtio-net-enable-virtio-1.0.patch [bz#1248312]
- kvm-virtio-net-unbreak-any-layout.patch [bz#1248312]
- kvm-virtio-hide-legacy-features-from-modern-guests.patch [bz#1248312]
- kvm-virtio-serial-fix-ANY_LAYOUT.patch [bz#1248312]
- kvm-virtio-9p-fix-any_layout.patch [bz#1248312]
- kvm-virtio-set-any_layout-in-virtio-core.patch [bz#1248312]
- kvm-virtio-pci-fix-memory-MR-cleanup-for-modern.patch [bz#1248312]
- kvm-virtio-get_features-can-fail.patch [bz#1248312]
- kvm-virtio-blk-fail-get_features-when-both-scsi-and-1.0-.patch [bz#1248312]
- kvm-virtio-minor-cleanup.patch [bz#1248312]
- kvm-memory-do-not-add-a-reference-to-the-owner-of-aliase.patch [bz#1248312]
- kvm-virtio-net-remove-virtio-queues-if-the-guest-doesn-t.patch [bz#1248312]
- kvm-virtio-fix-1.0-virtqueue-migration.patch [bz#1248312]
- kvm-Downstream-only-Start-kvm-setup-service-before-libvi.patch [bz#1251962]
- kvm-qcow2-Flush-pending-discards-before-allocating-clust.patch [bz#1226297]
- Resolves: bz#1226297
  (qcow2 crash during discard operation)
- Resolves: bz#1248312
  ("fdisk -l"can not output anything and the process status is D+ after migrating RHEL7.2 guest with virtio-1 virtio-scsi disk)
- Resolves: bz#1251962
  (kvm-setup.service should include Before=libvirtd.service)

* Wed Aug 12 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-17.el7
- kvm-migration-avoid-divide-by-zero-in-xbzrle-cache-miss-.patch [bz#580006]
- kvm-migration-move-ram-stuff-to-migration-ram.patch [bz#580006]
- kvm-migration-move-savevm.c-inside-migration.patch [bz#580006]
- kvm-migration-Add-myself-to-the-copyright-list-of-both-f.patch [bz#580006]
- kvm-migration-reduce-include-files.patch [bz#580006]
- kvm-migration-Remove-duplicated-assignment-of-SETUP-stat.patch [bz#580006]
- kvm-migration-create-savevm_state.patch [bz#580006]
- kvm-migration-Use-normal-VMStateDescriptions-for-Subsect.patch [bz#580006]
- kvm-Add-qemu_get_counted_string-to-read-a-string-prefixe.patch [bz#580006]
- kvm-runstate-Add-runstate-store.patch [bz#580006]
- kvm-runstate-migration-allows-more-transitions-now.patch [bz#580006]
- kvm-migration-create-new-section-to-store-global-state.patch [bz#580006]
- kvm-global_state-Make-section-optional.patch [bz#580006]
- kvm-vmstate-Create-optional-sections.patch [bz#580006]
- kvm-migration-Add-configuration-section.patch [bz#580006]
- kvm-migration-ensure-we-start-in-NONE-state.patch [bz#580006]
- kvm-migration-Use-always-helper-to-set-state.patch [bz#580006]
- kvm-migration-No-need-to-call-trace_migrate_set_state.patch [bz#580006]
- kvm-migration-create-migration-event.patch [bz#580006]
- kvm-migration-Make-events-a-capability.patch [bz#580006]
- kvm-migration-Add-migration-events-on-target-side.patch [bz#580006]
- kvm-migration-Only-change-state-after-migration-has-fini.patch [bz#580006]
- kvm-migration-Trace-event-and-migration-event-are-differ.patch [bz#580006]
- kvm-migration-Write-documetation-for-events-capabilites.patch [bz#580006]
- kvm-migration-Register-global-state-section-before-loadv.patch [bz#580006]
- kvm-migration-We-also-want-to-store-the-global-state-for.patch [bz#580006]
- kvm-block-mirror-limit-qiov-to-IOV_MAX-elements.patch [bz#1238585]
- kvm-i6300esb-fix-timer-overflow.patch [bz#1247893]
- Resolves: bz#1238585
  (drive-mirror has spurious failures with low 'granularity' values)
- Resolves: bz#1247893
  (qemu's i6300esb watchdog does not fire on time with large heartbeat like 2046)
- Resolves: bz#580006
  (QMP: A QMP event notification when migration finish.)

* Fri Aug 07 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-16.el7
- kvm-virtio-scsi-use-virtqueue_map_sg-when-loading-reques.patch [bz#1160169]
- kvm-scsi-disk-fix-cmd.mode-field-typo.patch [bz#1160169]
- kvm-target-i386-emulate-CPUID-level-of-real-hardware.patch [bz#1223317]
- kvm-target-i386-fix-IvyBridge-xlevel-in-PC_COMPAT_2_3.patch [bz#1223317]
- Resolves: bz#1160169
  (Segfault occurred at Dst VM while completed migration upon ENOSPC)
- Resolves: bz#1223317
  (BSod occurs When installing latest Windows Enterprise Insider 10 and windows server 2016 Preview)

* Wed Aug 05 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-15.el7
- kvm-usb-ccid-add-missing-wakeup-calls.patch [bz#1211970]
- kvm-vfio-pci-Fix-bootindex.patch [bz#1245127]
- kvm-acpi-fix-pvpanic-device-is-not-shown-in-ui.patch [bz#1238141]
- kvm-redhat-add-kvm-unit-tests-tarball-to-environment.patch [bz#1225980]
- kvm-spec-Build-tscdeadline_latency.flat-from-kvm-unit-te.patch [bz#1225980]
- Resolves: bz#1211970
  (smart card emulation doesn't work with USB3 (nec-xhci) controller)
- Resolves: bz#1225980
  (Package tscdeadline_latency.flat with qemu-kvm-rhev)
- Resolves: bz#1238141
  ([virtio-win][pvpanic]win10-32 guest can not detect pvpanic device in device manager)
- Resolves: bz#1245127
  (bootindex doesn't work for vfio-pci)

* Fri Jul 31 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-14.el7
- kvm-rtl8139-avoid-nested-ifs-in-IP-header-parsing-CVE-20.patch [bz#1248768]
- kvm-rtl8139-drop-tautologous-if-ip-.-statement-CVE-2015-.patch [bz#1248768]
- kvm-rtl8139-skip-offload-on-short-Ethernet-IP-header-CVE.patch [bz#1248768]
- kvm-rtl8139-check-IP-Header-Length-field-CVE-2015-5165.patch [bz#1248768]
- kvm-rtl8139-check-IP-Total-Length-field-CVE-2015-5165.patch [bz#1248768]
- kvm-rtl8139-skip-offload-on-short-TCP-header-CVE-2015-51.patch [bz#1248768]
- kvm-rtl8139-check-TCP-Data-Offset-field-CVE-2015-5165.patch [bz#1248768]
- Resolves: bz#1248768
  (EMBARGOED CVE-2015-5165 qemu-kvm-rhev: Qemu: rtl8139 uninitialized heap memory information leakage to guest [rhel-7.2])

* Fri Jul 24 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-13.el7
- kvm-block-Add-bdrv_get_block_status_above.patch [bz#1242316]
- kvm-qmp-Add-optional-bool-unmap-to-drive-mirror.patch [bz#1242316]
- kvm-mirror-Do-zero-write-on-target-if-sectors-not-alloca.patch [bz#1242316]
- kvm-block-Fix-dirty-bitmap-in-bdrv_co_discard.patch [bz#1242316]
- kvm-block-Remove-bdrv_reset_dirty.patch [bz#1242316]
- kvm-iotests-add-QMP-event-waiting-queue.patch [bz#1242316]
- kvm-qemu-iotests-Make-block-job-methods-common.patch [bz#1242316]
- kvm-qemu-iotests-Add-test-case-for-mirror-with-unmap.patch [bz#1242316]
- kvm-iotests-Use-event_wait-in-wait_ready.patch [bz#1242316]
- kvm-rdma-fix-memory-leak.patch [bz#1210715]
- kvm-Only-try-and-read-a-VMDescription-if-it-should-be-th.patch [bz#1210715]
- kvm-qemu_ram_foreach_block-pass-up-error-value-and-down-.patch [bz#1210715]
- kvm-rdma-Fix-qemu-crash-when-IPv6-address-is-used-for-mi.patch [bz#1210715]
- kvm-Rename-RDMA-structures-to-make-destination-clear.patch [bz#1210715]
- kvm-Remove-unneeded-memset.patch [bz#1210715]
- kvm-rdma-typos.patch [bz#1210715]
- kvm-Store-block-name-in-local-blocks-structure.patch [bz#1210715]
- kvm-Translate-offsets-to-destination-address-space.patch [bz#1210715]
- kvm-Rework-ram_control_load_hook-to-hook-during-block-lo.patch [bz#1210715]
- kvm-Allow-rdma_delete_block-to-work-without-the-hash.patch [bz#1210715]
- kvm-Rework-ram-block-hash.patch [bz#1210715]
- kvm-Sort-destination-RAMBlocks-to-be-the-same-as-the-sou.patch [bz#1210715]
- kvm-Sanity-check-RDMA-remote-data.patch [bz#1210715]
- kvm-Fail-more-cleanly-in-mismatched-RAM-cases.patch [bz#1210715]
- kvm-migration-Use-cmpxchg-correctly.patch [bz#1210715]
- kvm-RDMA-Fix-error-exits-for-2.4.patch [bz#1210715]
- kvm-block-mirror-Sleep-periodically-during-bitmap-scanni.patch [bz#1233826]
- kvm-block-curl-Don-t-lose-original-error-when-a-connecti.patch [bz#1235813]
- kvm-vfio-pci-Add-pba_offset-PCI-quirk-for-Chelsio-T5-dev.patch [bz#1244348]
- kvm-hostmem-Fix-qemu_opt_get_bool-crash-in-host_memory_b.patch [bz#1237220]
- kvm-pc-pc-dimm-Extract-hotplug-related-fields-in-PCMachi.patch [bz#1211117]
- kvm-pc-pc-dimm-Factor-out-reusable-parts-in-pc_dimm_plug.patch [bz#1211117]
- kvm-pc-Abort-if-HotplugHandlerClass-plug-fails.patch [bz#1211117]
- kvm-numa-pc-dimm-Store-pc-dimm-memory-information-in-num.patch [bz#1211117]
- kvm-numa-Store-boot-memory-address-range-in-node_info.patch [bz#1211117]
- kvm-numa-API-to-lookup-NUMA-node-by-address.patch [bz#1211117]
- kvm-docs-add-sPAPR-hotplug-dynamic-reconfiguration-docum.patch [bz#1211117]
- kvm-machine-add-default_ram_size-to-machine-class.patch [bz#1211117]
- kvm-spapr-override-default-ram-size-to-512MB.patch [bz#1211117]
- kvm-spapr_pci-Make-find_phb-find_dev-public.patch [bz#1211117]
- kvm-spapr-Merge-sPAPREnvironment-into-sPAPRMachineState.patch [bz#1211117]
- kvm-spapr-Remove-obsolete-ram_limit-field-from-sPAPRMach.patch [bz#1211117]
- kvm-spapr-Remove-obsolete-entry_point-field-from-sPAPRMa.patch [bz#1211117]
- kvm-spapr-Add-sPAPRMachineClass.patch [bz#1211117]
- kvm-spapr-ensure-we-have-at-least-one-XICS-server.patch [bz#1211117]
- kvm-spapr-Consider-max_cpus-during-xics-initialization.patch [bz#1211117]
- kvm-spapr-Support-ibm-lrdr-capacity-device-tree-property.patch [bz#1211117]
- kvm-cpus-Add-a-macro-to-walk-CPUs-in-reverse.patch [bz#1211117]
- kvm-spapr-Reorganize-CPU-dt-generation-code.patch [bz#1211117]
- kvm-spapr-Consolidate-cpu-init-code-into-a-routine.patch [bz#1211117]
- kvm-ppc-Update-cpu_model-in-MachineState.patch [bz#1211117]
- kvm-xics_kvm-Don-t-enable-KVM_CAP_IRQ_XICS-if-already-en.patch [bz#1211117]
- kvm-spapr-Initialize-hotplug-memory-address-space.patch [bz#1211117]
- kvm-spapr-Add-LMB-DR-connectors.patch [bz#1211117]
- kvm-spapr-Support-ibm-dynamic-reconfiguration-memory.patch [bz#1211117]
- kvm-spapr-Make-hash-table-size-a-factor-of-maxram_size.patch [bz#1211117]
- kvm-spapr-Memory-hotplug-support.patch [bz#1211117]
- kvm-spapr-Don-t-allow-memory-hotplug-to-memory-less-node.patch [bz#1211117]
- Resolves: bz#1210715
  (migration/rdma: 7.1->7.2: RDMA ERROR: ram blocks mismatch #3!)
- Resolves: bz#1211117
  (add support for memory hotplug on Power)
- Resolves: bz#1233826
  (issueing drive-mirror command causes monitor unresponsive)
- Resolves: bz#1235813
  (block/curl: Fix generic "Input/output error" on failure)
- Resolves: bz#1237220
  (Fail to create NUMA guest with <nosharepages/>)
- Resolves: bz#1242316
  (Add "unmap" support for drive-mirror)
- Resolves: bz#1244348
  (Quirk for Chelsio T5 MSI-X PBA)

* Fri Jul 17 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-12.el7
- kvm-ide-Check-array-bounds-before-writing-to-io_buffer-C.patch [bz#1243692]
- kvm-ide-atapi-Fix-START-STOP-UNIT-command-completion.patch [bz#1243692]
- kvm-ide-Clear-DRQ-after-handling-all-expected-accesses.patch [bz#1243692]
- Resolves: bz#1243692
  ()

* Fri Jul 17 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-11.el7
- kvm-hw-acpi-acpi_pm1_cnt_init-take-disable_s3-and-disabl.patch [bz#1204696]
- kvm-hw-acpi-move-etc-system-states-fw_cfg-file-from-PIIX.patch [bz#1204696]
- kvm-hw-acpi-piix4_pm_init-take-fw_cfg-object-no-more.patch [bz#1204696]
- kvm-i386-pc-pc_basic_device_init-delegate-FDC-creation-r.patch [bz#1227282]
- kvm-i386-pc-drive-if-floppy-should-imply-a-board-default.patch [bz#1227282]
- kvm-i386-pc_q35-don-t-insist-on-board-FDC-if-there-s-no-.patch [bz#1227282]
- kvm-i386-drop-FDC-in-pc-q35-rhel7.2.0-if-neither-it-nor-.patch [bz#1227282]
- kvm-hw-i386-pc-factor-out-pc_cmos_init_floppy.patch [bz#1227282]
- kvm-hw-i386-pc-reflect-any-FDC-ioport-0x3f0-in-the-CMOS.patch [bz#1227282]
- kvm-hw-i386-pc-don-t-carry-FDC-from-pc_basic_device_init.patch [bz#1227282]
- kvm-Fix-reported-machine-type.patch [bz#1241331]
- kvm-i386-acpi-build-more-traditional-_UID-and-_HID-for-P.patch [bz#1242479]
- kvm-i386-acpi-build-fix-PXB-workarounds-for-unsupported-.patch [bz#1242479]
- kvm-hw-core-rebase-sysbus_get_fw_dev_path-to-g_strdup_pr.patch [bz#1242479]
- kvm-migration-introduce-VMSTATE_BUFFER_UNSAFE_INFO_TEST.patch [bz#1242479]
- kvm-hw-pci-bridge-expose-_test-parameter-in-SHPC_VMSTATE.patch [bz#1242479]
- kvm-hw-pci-bridge-add-macro-for-chassis_nr-property.patch [bz#1242479]
- kvm-hw-pci-bridge-add-macro-for-msi-property.patch [bz#1242479]
- kvm-hw-pci-introduce-shpc_present-helper-function.patch [bz#1242479]
- kvm-hw-pci-bridge-introduce-shpc-property.patch [bz#1242479]
- kvm-hw-pci-bridge-disable-SHPC-in-PXB.patch [bz#1242479]
- kvm-hw-core-explicit-OFW-unit-address-callback-for-SysBu.patch [bz#1242479]
- kvm-hw-pci-bridge-format-special-OFW-unit-address-for-PX.patch [bz#1242479]
- Resolves: bz#1204696
  (Expose PM system states in fw_cfg file on Q35)
- Resolves: bz#1227282
  (tighten conditions for board-implied FDC in pc-q35-rhel7.2.0+)
- Resolves: bz#1241331
  (Machine type reported by guest is different with that in RHEL.7.1 GA version)
- Resolves: bz#1242479
  (backport QEMU changes needed for supporting multiple PCI root buses with OVMF)

* Tue Jul 14 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-10.el7
- kvm-Disable-Educational-device.patch [bz#1194151]
- kvm-Disable-sdhci-device.patch [bz#1194151]
- kvm-Mark-onboard-devices-as-cannot_instantiate_with_devi.patch [bz#1194151]
- kvm-target-arm-Add-GIC-phandle-to-VirtBoardInfo.patch [bz#1231929]
- kvm-arm_gicv2m-Add-GICv2m-widget-to-support-MSIs.patch [bz#1231929]
- kvm-target-arm-Extend-the-gic-node-properties.patch [bz#1231929]
- kvm-target-arm-Add-the-GICv2m-to-the-virt-board.patch [bz#1231929]
- kvm-introduce-kvm_arch_msi_data_to_gsi.patch [bz#1231929]
- kvm-arm_gicv2m-set-kvm_gsi_direct_mapping-and-kvm_msi_vi.patch [bz#1231929]
- kvm-hw-arm-virt-acpi-build-Fix-table-revision-and-some-c.patch [bz#1231929]
- kvm-hw-arm-virt-acpi-build-Add-GICv2m-description-in-ACP.patch [bz#1231929]
- Resolves: bz#1194151
  (Rebase to qemu 2.3)
- Resolves: bz#1231929
  (AArch64: backport MSI support (gicv2m))

* Thu Jul 09 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-9.el7
- kvm-acpi-add-a-missing-backslash-to-the-_SB-scope.patch [bz#1103313]
- kvm-range-remove-useless-inclusions.patch [bz#1103313]
- kvm-acpi-Simplify-printing-to-dynamic-string.patch [bz#1103313]
- kvm-acpi-add-aml_add-term.patch [bz#1103313]
- kvm-acpi-add-aml_lless-term.patch [bz#1103313]
- kvm-acpi-add-aml_index-term.patch [bz#1103313]
- kvm-acpi-add-aml_shiftleft-term.patch [bz#1103313]
- kvm-acpi-add-aml_shiftright-term.patch [bz#1103313]
- kvm-acpi-add-aml_increment-term.patch [bz#1103313]
- kvm-acpi-add-aml_while-term.patch [bz#1103313]
- kvm-acpi-add-implementation-of-aml_while-term.patch [bz#1103313]
- kvm-hw-pci-made-pci_bus_is_root-a-PCIBusClass-method.patch [bz#1103313]
- kvm-hw-pci-made-pci_bus_num-a-PCIBusClass-method.patch [bz#1103313]
- kvm-hw-i386-query-only-for-q35-pc-when-looking-for-pci-h.patch [bz#1103313]
- kvm-hw-pci-extend-PCI-config-access-to-support-devices-b.patch [bz#1103313]
- kvm-hw-acpi-add-support-for-i440fx-snooping-root-busses.patch [bz#1103313]
- kvm-hw-apci-add-_PRT-method-for-extra-PCI-root-busses.patch [bz#1103313]
- kvm-hw-acpi-add-_CRS-method-for-extra-root-busses.patch [bz#1103313]
- kvm-hw-acpi-remove-from-root-bus-0-the-crs-resources-use.patch [bz#1103313]
- kvm-hw-pci-removed-rootbus-nr-is-0-assumption-from-qmp_p.patch [bz#1103313]
- kvm-hw-pci-introduce-PCI-Expander-Bridge-PXB.patch [bz#1103313]
- kvm-hw-pci-inform-bios-if-the-system-has-extra-pci-root-.patch [bz#1103313]
- kvm-hw-pxb-add-map_irq-func.patch [bz#1103313]
- kvm-hw-pci-add-support-for-NUMA-nodes.patch [bz#1103313]
- kvm-hw-pxb-add-numa_node-parameter.patch [bz#1103313]
- kvm-apci-fix-PXB-behaviour-if-used-with-unsupported-BIOS.patch [bz#1103313]
- kvm-docs-Add-PXB-documentation.patch [bz#1103313]
- kvm-sPAPR-Don-t-enable-EEH-on-emulated-PCI-devices.patch [bz#1213681]
- kvm-sPAPR-Reenable-EEH-functionality-on-reboot.patch [bz#1213681]
- kvm-sPAPR-Clear-stale-MSIx-table-during-EEH-reset.patch [bz#1213681]
- kvm-configure-Add-support-for-tcmalloc.patch [bz#1213882]
- Resolves: bz#1103313
  (RFE: configure guest NUMA node locality for guest PCI devices)
- Resolves: bz#1213681
  (PAPR PCI-e EEH (Enhanced Error Handling) for KVM/Power guests with VFIO devices (qemu))
- Resolves: bz#1213882
  (enable using tcmalloc for memory allocation in qemu-kvm-rhev)

* Wed Jul 08 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-8.el7
- kvm-block-Fix-NULL-deference-for-unaligned-write-if-qiov.patch [bz#1207034]
- kvm-qemu-iotests-Test-unaligned-sub-block-zero-write.patch [bz#1207034]
- kvm-spapr_drc-initial-implementation-of-sPAPRDRConnector.patch [bz#1172478]
- kvm-spapr_rtas-add-get-set-power-level-RTAS-interfaces.patch [bz#1172478]
- kvm-spapr_rtas-add-set-indicator-RTAS-interface.patch [bz#1172478]
- kvm-spapr_rtas-add-get-sensor-state-RTAS-interface.patch [bz#1172478]
- kvm-spapr-add-rtas_st_buffer_direct-helper.patch [bz#1172478]
- kvm-spapr_rtas-add-ibm-configure-connector-RTAS-interfac.patch [bz#1172478]
- kvm-spapr_events-re-use-EPOW-event-infrastructure-for-ho.patch [bz#1172478]
- kvm-spapr_events-event-scan-RTAS-interface.patch [bz#1172478]
- kvm-spapr_drc-add-spapr_drc_populate_dt.patch [bz#1172478]
- kvm-spapr_pci-add-dynamic-reconfiguration-option-for-spa.patch [bz#1172478]
- kvm-spapr_pci-create-DRConnectors-for-each-PCI-slot-duri.patch [bz#1172478]
- kvm-pci-make-pci_bar-useable-outside-pci.c.patch [bz#1172478]
- kvm-spapr_pci-enable-basic-hotplug-operations.patch [bz#1172478]
- kvm-spapr_pci-emit-hotplug-add-remove-events-during-hotp.patch [bz#1172478]
- kvm-Print-error-when-failing-to-load-PCI-config-data.patch [bz#1209793]
- kvm-Fix-ich9-intel-hda-compatibility.patch [bz#1209793]
- kvm-pseries-Enable-in-kernel-H_LOGICAL_CI_-LOAD-STORE-im.patch [bz#1217277]
- kvm-Split-serial-isa-into-its-own-config-option.patch [bz#1191845]
- kvm-rhel-Disable-info-irq-and-info-pic-for-Power.patch [bz#1191845]
- kvm-RHEL-Disable-remaining-unsupported-devices-for-ppc.patch [bz#1191845]
- kvm-linux-headers-sync-vhost.h.patch [bz#1225715]
- kvm-virtio-introduce-virtio_legacy_is_cross_endian.patch [bz#1225715]
- kvm-vhost-set-vring-endianness-for-legacy-virtio.patch [bz#1225715]
- kvm-tap-add-VNET_LE-VNET_BE-operations.patch [bz#1225715]
- kvm-tap-fix-non-linux-build.patch [bz#1225715]
- kvm-vhost-net-tell-tap-backend-about-the-vnet-endianness.patch [bz#1225715]
- kvm-vhost_net-re-enable-when-cross-endian.patch [bz#1225715]
- kvm-linux-headers-update.patch [bz#1227343]
- kvm-virtio-input-add-linux-input.h.patch [bz#1227343]
- kvm-virtio-input-core-code-base-class-device.patch [bz#1227343]
- kvm-virtio-input-emulated-devices-device.patch [bz#1227343]
- kvm-virtio-net-Move-DEFINE_VIRTIO_NET_FEATURES-to-virtio.patch [bz#1227343]
- kvm-virtio-scsi-Move-DEFINE_VIRTIO_SCSI_FEATURES-to-virt.patch [bz#1227343]
- kvm-memory-Define-API-for-MemoryRegionOps-to-take-attrs-.patch [bz#1227343]
- kvm-memory-Replace-io_mem_read-write-with-memory_region_.patch [bz#1227343]
- kvm-Make-CPU-iotlb-a-structure-rather-than-a-plain-hwadd.patch [bz#1227343]
- kvm-Add-MemTxAttrs-to-the-IOTLB.patch [bz#1227343]
- kvm-exec.c-Convert-subpage-memory-ops-to-_with_attrs.patch [bz#1227343]
- kvm-exec.c-Make-address_space_rw-take-transaction-attrib.patch [bz#1227343]
- kvm-exec.c-Add-new-address_space_ld-st-functions.patch [bz#1227343]
- kvm-Switch-non-CPU-callers-from-ld-st-_phys-to-address_s.patch [bz#1227343]
- kvm-s390-virtio-sort-into-categories.patch [bz#1227343]
- kvm-s390-virtio-use-common-features.patch [bz#1227343]
- kvm-virtio-move-host_features.patch [bz#1227343]
- kvm-virtio-ccw-Don-t-advertise-VIRTIO_F_BAD_FEATURE.patch [bz#1227343]
- kvm-virtio-move-VIRTIO_F_NOTIFY_ON_EMPTY-into-core.patch [bz#1227343]
- kvm-qdev-add-64bit-properties.patch [bz#1227343]
- kvm-virtio-make-features-64bit-wide.patch [bz#1227343]
- kvm-virtio-input-const_le16-and-const_le32-not-build-tim.patch [bz#1227343]
- kvm-virtio-input-make-virtio-devices-follow-usual-naming.patch [bz#1227343]
- kvm-virtio-64bit-features-fixups.patch [bz#1227343]
- kvm-virtio-endianness-checks-for-virtio-1.0-devices.patch [bz#1227343]
- kvm-virtio-allow-virtio-1-queue-layout.patch [bz#1227343]
- kvm-virtio-disallow-late-feature-changes-for-virtio-1.patch [bz#1227343]
- kvm-virtio-allow-to-fail-setting-status.patch [bz#1227343]
- kvm-virtio-net-no-writeable-mac-for-virtio-1.patch [bz#1227343]
- kvm-virtio-net-support-longer-header.patch [bz#1227343]
- kvm-virtio-net-enable-virtio-1.0.patch [bz#1227343]
- kvm-vhost_net-add-version_1-feature.patch [bz#1227343]
- kvm-vhost-64-bit-features.patch [bz#1227343]
- kvm-linux-headers-add-virtio_pci.patch [bz#1227343]
- kvm-virtio-pci-initial-virtio-1.0-support.patch [bz#1227343]
- kvm-virtio-generation-counter-support.patch [bz#1227343]
- kvm-virtio-add-modern-config-accessors.patch [bz#1227343]
- kvm-virtio-pci-switch-to-modern-accessors-for-1.0.patch [bz#1227343]
- kvm-virtio-pci-add-flags-to-enable-disable-legacy-modern.patch [bz#1227343]
- kvm-virtio-pci-make-QEMU_VIRTIO_PCI_QUEUE_MEM_MULT-small.patch [bz#1227343]
- kvm-virtio-pci-change-document-virtio-pci-bar-layout.patch [bz#1227343]
- kvm-virtio-pci-make-modern-bar-64bit-prefetchable.patch [bz#1227343]
- kvm-virtio-pci-correctly-set-host-notifiers-for-modern-b.patch [bz#1227343]
- kvm-virtio_balloon-header-update.patch [bz#1227343]
- kvm-virtio-balloon-switch-to-virtio_add_feature.patch [bz#1227343]
- kvm-virtio-pci-add-struct-VirtIOPCIRegion-for-virtio-1-r.patch [bz#1227343]
- kvm-virtio-pci-add-virtio_pci_modern_regions_init.patch [bz#1227343]
- kvm-virtio-pci-add-virtio_pci_modern_region_map.patch [bz#1227343]
- kvm-virtio-pci-move-virtio_pci_add_mem_cap-call-to-virti.patch [bz#1227343]
- kvm-virtio-pci-move-cap-type-to-VirtIOPCIRegion.patch [bz#1227343]
- kvm-virtio-pci-drop-identical-virtio_pci_cap.patch [bz#1227343]
- kvm-virtio-pci-fill-VirtIOPCIRegions-early.patch [bz#1227343]
- kvm-pci-add-PCI_CLASS_INPUT_.patch [bz#1227343]
- kvm-virtio-input-core-code-base-class-pci.patch [bz#1227343]
- kvm-virtio-input-emulated-devices-pci.patch [bz#1227343]
- kvm-virtio-net-move-qdev-properties-into-virtio-net.c.patch [bz#1227343]
- kvm-virtio-net.h-Remove-unsed-DEFINE_VIRTIO_NET_PROPERTI.patch [bz#1227343]
- kvm-virtio-scsi-move-qdev-properties-into-virtio-scsi.c.patch [bz#1227343]
- kvm-virtio-rng-move-qdev-properties-into-virtio-rng.c.patch [bz#1227343]
- kvm-virtio-serial-bus-move-qdev-properties-into-virtio-s.patch [bz#1227343]
- kvm-virtio-9p-device-move-qdev-properties-into-virtio-9p.patch [bz#1227343]
- kvm-vhost-scsi-move-qdev-properties-into-vhost-scsi.c.patch [bz#1227343]
- kvm-virito-pci-fix-OVERRUN-problem.patch [bz#1227343]
- kvm-virtio-input-move-properties-use-virtio_instance_ini.patch [bz#1227343]
- kvm-virtio-input-evdev-passthrough.patch [bz#1227343]
- kvm-Add-MAINTAINERS-entry-for-virtio-input.patch [bz#1227343]
- kvm-virtio-input-add-input-routing-support.patch [bz#1227343]
- kvm-dataplane-fix-cross-endian-issues.patch [bz#1227343]
- kvm-aarch64-allow-enable-seccomp.patch [bz#1174861]
- kvm-aarch64-redhat-spec-enable-seccomp.patch [bz#1174861]
- kvm-rhel-Update-package-version-for-SLOF-dependency.patch [bz#1236447]
- Resolves: bz#1172478
  (add support for PCI hotplugging)
- Resolves: bz#1174861
  (use seccomp)
- Resolves: bz#1191845
  ([PowerKVM] There are some unsupported x86 devices under the output of cmds 'man qemu-kvm' and '/usr/libexec/qemu-kvm -device help')
- Resolves: bz#1207034
  (QEMU segfault when doing unaligned zero write to non-512 disk)
- Resolves: bz#1209793
  (migration: 7.1->7.2 error while loading state for instance 0x0 of device '0000:00:04.0/intel-hda')
- Resolves: bz#1217277
  (Enable KVM implementation of H_LOGICAL_CI_{LOAD,STORE})
- Resolves: bz#1225715
  (Enable cross-endian vhost devices)
- Resolves: bz#1227343
  ([virtio-1] QEMU Virtio-1 Support)
- Resolves: bz#1236447
  (Update qemu-kvm-rhev package for new SLOF)

* Thu Jul 02 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-7.el7
- kvm-docs-update-documentation-for-memory-hot-unplug.patch [bz#1120706]
- kvm-acpi-mem-hotplug-add-acpi_memory_slot_status-to-get-.patch [bz#1120706]
- kvm-acpi-mem-hotplug-add-unplug-request-cb-for-memory-de.patch [bz#1120706]
- kvm-acpi-mem-hotplug-add-unplug-cb-for-memory-device.patch [bz#1120706]
- kvm-acpi-extend-aml_field-to-support-UpdateRule.patch [bz#1120706]
- kvm-acpi-fix-Memory-device-control-fields-register.patch [bz#1120706]
- kvm-acpi-add-hardware-implementation-for-memory-hot-unpl.patch [bz#1120706]
- kvm-qmp-event-add-event-notification-for-memory-hot-unpl.patch [bz#1120706]
- kvm-hw-acpi-aml-build-Fix-memory-leak.patch [bz#1120706]
- kvm-memory-add-memory_region_ram_resize.patch [bz#1231719]
- kvm-acpi-build-remove-dependency-from-ram_addr.h.patch [bz#1231719]
- kvm-hw-i386-Move-ACPI-header-definitions-in-an-arch-inde.patch [bz#1231719]
- kvm-hw-i386-acpi-build-move-generic-acpi-building-helper.patch [bz#1231719]
- kvm-hw-acpi-aml-build-Make-enum-values-to-be-upper-case-.patch [bz#1231719]
- kvm-hw-arm-virt-Move-common-definitions-to-virt.h.patch [bz#1231719]
- kvm-hw-arm-virt-Record-PCIe-ranges-in-MemMapEntry-array.patch [bz#1231719]
- kvm-hw-arm-virt-acpi-build-Basic-framework-for-building-.patch [bz#1231719]
- kvm-hw-acpi-aml-build-Add-aml_memory32_fixed-term.patch [bz#1231719]
- kvm-hw-acpi-aml-build-Add-aml_interrupt-term.patch [bz#1231719]
- kvm-hw-arm-virt-acpi-build-Generation-of-DSDT-table-for-.patch [bz#1231719]
- kvm-hw-arm-virt-acpi-build-Generate-FADT-table-and-updat.patch [bz#1231719]
- kvm-hw-arm-virt-acpi-build-Generate-MADT-table.patch [bz#1231719]
- kvm-hw-arm-virt-acpi-build-Generate-GTDT-table.patch [bz#1231719]
- kvm-hw-arm-virt-acpi-build-Generate-RSDT-table.patch [bz#1231719]
- kvm-hw-arm-virt-acpi-build-Generate-RSDP-table.patch [bz#1231719]
- kvm-hw-arm-virt-acpi-build-Generate-MCFG-table.patch [bz#1231719]
- kvm-hw-acpi-aml-build-Make-aml_buffer-definition-consist.patch [bz#1231719]
- kvm-hw-acpi-aml-build-Add-ToUUID-macro.patch [bz#1231719]
- kvm-hw-acpi-aml-build-Add-aml_or-term.patch [bz#1231719]
- kvm-hw-acpi-aml-build-Add-aml_lnot-term.patch [bz#1231719]
- kvm-hw-acpi-aml-build-Add-aml_else-term.patch [bz#1231719]
- kvm-hw-acpi-aml-build-Add-aml_create_dword_field-term.patch [bz#1231719]
- kvm-hw-acpi-aml-build-Add-aml_dword_io-term.patch [bz#1231719]
- kvm-hw-acpi-aml-build-Add-Unicode-macro.patch [bz#1231719]
- kvm-hw-arm-virt-acpi-build-Add-PCIe-controller-in-ACPI-D.patch [bz#1231719]
- kvm-ACPI-split-CONFIG_ACPI-into-4-pieces.patch [bz#1231719]
- kvm-hw-arm-virt-Enable-dynamic-generation-of-ACPI-v5.1-t.patch [bz#1231719]
- kvm-ACPI-Add-definitions-for-the-SPCR-table.patch [bz#1231719]
- kvm-hw-arm-virt-acpi-build-Add-SPCR-table.patch [bz#1231719]
- kvm-AArch64-Enable-ACPI.patch [bz#1231719]
- kvm-i8254-fix-out-of-bounds-memory-access-in-pit_ioport_.patch [bz#1229647]
- kvm-hw-q35-fix-floppy-controller-definition-in-ich9.patch [bz#894956]
- kvm-Migration-compat-for-pckbd.patch [bz#1215092]
- kvm-Migration-compat-for-fdc.patch [bz#1215091]
- Resolves: bz#1120706
  (Support dynamic virtual Memory deallocation - qemu-kvm)
- Resolves: bz#1215091
  (migration: 7.2->earlier; floppy compatibility)
- Resolves: bz#1215092
  (migration: 7.2->earlier: pckbd compatibility)
- Resolves: bz#1229647
  (CVE-2015-3214 qemu-kvm-rhev: qemu: i8254: out-of-bounds memory access in pit_ioport_read function [rhel-7.2])
- Resolves: bz#1231719
  (AArch64: backport ACPI support)
- Resolves: bz#894956
  (floppy can not be recognized by Windows guest (q35))

* Fri Jun 26 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-6.el7
- kvm-vfio-pci-Fix-error-path-sign.patch [bz#1219090]
- kvm-vfio-pci-Further-fix-BAR-size-overflow.patch [bz#1219090]
- kvm-Add-flag-for-pre-2.2-migration-compatibility.patch [bz#1215087]
- kvm-Serial-Migration-compatibility-pre-2.2-7.2.patch [bz#1215087]
- kvm-Migration-compat-for-mc146818rtc-irq_reinject_on_ack.patch [bz#1215088]
- Resolves: bz#1215087
  (migration: 7.2->earlier;  serial compatibility)
- Resolves: bz#1215088
  (migration: 7.2->earlier; mc146818rtc compatibility)
- Resolves: bz#1219090
  (vfio-pci - post QEMU2.3 fixes, error sign + BAR overflow)

* Wed Jun 24 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-5.el7
- kvm-atomics-add-explicit-compiler-fence-in-__atomic-memo.patch [bz#1231335]
- kvm-pc-acpi-fix-pvpanic-for-buggy-guests.patch [bz#1221943]
- Resolves: bz#1221943
  (On_crash events didn't work when using guest's pvpanic device)
- Resolves: bz#1231335
  ([abrt] qemu-kvm: bdrv_error_action(): qemu-kvm killed by SIGABRT)

* Mon Jun 22 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-4.el7
- kvm-virtio-ccw-using-VIRTIO_NO_VECTOR-instead-of-0-for-i.patch [bz#1231610]
- kvm-virtio-ccw-sort-into-categories.patch [bz#1231610]
- kvm-virtio-ccw-change-realization-sequence.patch [bz#1231610]
- kvm-virtio-ccw-implement-device_plugged.patch [bz#1231610]
- kvm-virtio-net-fix-the-upper-bound-when-trying-to-delete.patch [bz#1231610]
- kvm-monitor-replace-the-magic-number-255-with-MAX_QUEUE_.patch [bz#1231610]
- kvm-monitor-check-return-value-of-qemu_find_net_clients_.patch [bz#1231610]
- kvm-virtio-introduce-vector-to-virtqueues-mapping.patch [bz#1231610]
- kvm-virtio-pci-speedup-MSI-X-masking-and-unmasking.patch [bz#1231610]
- kvm-pci-remove-hard-coded-bar-size-in-msix_init_exclusiv.patch [bz#1231610]
- kvm-virtio-net-adding-all-queues-in-.realize.patch [bz#1231610]
- kvm-virtio-device_plugged-can-fail.patch [bz#1231610]
- kvm-virtio-introduce-virtio_get_num_queues.patch [bz#1231610]
- kvm-virtio-ccw-introduce-ccw-specific-queue-limit.patch [bz#1231610]
- kvm-virtio-ccw-validate-the-number-of-queues-against-bus.patch [bz#1231610]
- kvm-virtio-s390-introduce-virito-s390-queue-limit.patch [bz#1231610]
- kvm-virtio-s390-introduce-virtio_s390_device_plugged.patch [bz#1231610]
- kvm-virtio-rename-VIRTIO_PCI_QUEUE_MAX-to-VIRTIO_QUEUE_M.patch [bz#1231610]
- kvm-virtio-increase-the-queue-limit-to-1024.patch [bz#1231610]
- kvm-virtio-pci-don-t-try-to-mask-or-unmask-vqs-without-n.patch [bz#1231610]
- Resolves: bz#1231610
  (Support more virtio queues)

* Fri Jun 19 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-3.el7
- kvm-vmdk-Fix-overflow-if-l1_size-is-0x20000000.patch [bz#1226809]
- kvm-Downstream-only-Add-rhel7.2.0-machine-type.patch [bz#1228574]
- kvm-spice-display-fix-segfault-in-qemu_spice_create_upda.patch [bz#1230550]
- kvm-pc-dimm-don-t-assert-if-pc-dimm-alignment-hotpluggab.patch [bz#1221425]
- kvm-Strip-brackets-from-vnc-host.patch [bz#1229073]
- kvm-qcow2-Set-MIN_L2_CACHE_SIZE-to-2.patch [bz#1226996]
- kvm-iotests-qcow2-COW-with-minimal-L2-cache-size.patch [bz#1226996]
- kvm-qcow2-Add-DEFAULT_L2_CACHE_CLUSTERS.patch [bz#1226996]
- kvm-spec-Ship-complete-QMP-documentation-files.patch [bz#1222834]
- Resolves: bz#1221425
  (qemu crash when hot-plug a memory device)
- Resolves: bz#1222834
  (We ship incomplete QMP documentation)
- Resolves: bz#1226809
  (Overflow in malloc size calculation in VMDK driver)
- Resolves: bz#1226996
  (qcow2: Fix minimum L2 cache size)
- Resolves: bz#1228574
  (Add RHEL7.2 machine type in QEMU for PPC64LE)
- Resolves: bz#1229073
  ([graphical framebuffer]Start guest failed when VNC listen on IPV6 address)
- Resolves: bz#1230550
  ([abrt] qemu-system-x86: __memcmp_sse4_1(): qemu-system-x86_64 killed by SIGSEGV)

* Wed May 27 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-2.el7
- kvm-balloon-improve-error-msg-when-adding-second-device.patch [bz#1165534]
- kvm-qmp-add-error-reason-to-the-BLOCK_IO_ERROR-event.patch [bz#1199174]
- kvm-spec-Remove-obsolete-differentiation-code.patch [bz#1122778]
- kvm-spec-Use-external-configuration-script.patch [bz#1122778]
- kvm-spec-Use-configure-options-to-prevent-default-resolu.patch [bz#1122778]
- kvm-fdc-force-the-fifo-access-to-be-in-bounds-of-the-all.patch [bz#1219272]
- Resolves: bz#1122778
  (miss  "vhdx" and "iscsi" in qemu-img supported format list)
- Resolves: bz#1165534
  (balloon: improve error message when adding second device)
- Resolves: bz#1199174
  (QMP: forward port rhel-only error reason to BLOCK_IO_ERROR event)
- Resolves: bz#1219272
  (CVE-2015-3456 qemu-kvm-rhev: qemu: floppy disk controller flaw [rhel-7.2])

* Tue Apr 28 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.3.0-1.el7
- Rebase to 2.3.0 [bz#1194151]
- kvm-misc-Add-pc-i440fx-rhel7-2-0-machine-type.patch [bz#1210050]
- kvm-misc-Add-pc-q35-rhel7-2-0-machine-type.patch [bz#1210050]
- Resolves: bz#1194151
  (Rebase to qemu 2.3)
- Resolves: bz#1210050
  (Add pc-i440fx-rhel7.2.0 machine type)

* Thu Mar 19 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.2.0-8.el7
- kvm-pc_sysfw-prevent-pflash-and-or-mis-sized-firmware-fo.patch [bz#1175099]
- kvm-build-reenable-local-builds-to-pass-enable-debug-dow.patch []
- kvm-RPM-spec-install-dump-guest-memory.py-downstream-onl.patch [bz#1194304]
- kvm-vga-Expose-framebuffer-byteorder-as-a-QOM-property.patch [bz#1146809]
- kvm-pseries-Switch-VGA-endian-on-H_SET_MODE.patch [bz#1146809]
- kvm-Generalize-QOM-publishing-of-date-and-time-from-mc14.patch [bz#1172583]
- kvm-Add-more-VMSTATE_-_TEST-variants-for-integers.patch [bz#1171700]
- kvm-pseries-Move-sPAPR-RTC-code-into-its-own-file.patch [bz#1170132 bz#1171700 bz#1172583]
- kvm-pseries-Add-more-parameter-validation-in-RTAS-time-o.patch [bz#1170132 bz#1171700 bz#1172583]
- kvm-pseries-Add-spapr_rtc_read-helper-function.patch [bz#1170132 bz#1171700 bz#1172583]
- kvm-pseries-Make-RTAS-time-of-day-functions-respect-rtc-.patch [bz#1170132]
- kvm-pseries-Make-the-PAPR-RTC-a-qdev-device.patch [bz#1170132 bz#1171700 bz#1172583]
- kvm-pseries-Move-rtc_offset-into-RTC-device-s-state-stru.patch [bz#1171700]
- kvm-pseries-Export-RTC-time-via-QOM.patch [bz#1172583]
- kvm-pseries-Limit-PCI-host-bridge-index-value.patch [bz#1181409]
- Resolves: bz#1146809
  (Incorrect colours on virtual VGA with ppc64le guest under ppc64 host)
- Resolves: bz#1170132
  (Guest time could change with host time even specify the guest clock as "-rtc base=utc,clock=vm,...")
- Resolves: bz#1171700
  ('hwclock' in destination guest returns to base '2006-06-06' after migration)
- Resolves: bz#1172583
  ([Power KVM] Qemu monitor command don't support {"execute":"qom-get","arguments":{"path":"/machine","property":"rtc-time"}})
- Resolves: bz#1175099
  ([migration]migration failed when configure guest with OVMF bios + machine type=rhel6.5.0)
- Resolves: bz#1181409
  (PCI pass-through device works improperly due to the PHB's index being set to a big value)
- Resolves: bz#1194304
  ([Hitachi 7.2 FEAT] Extract guest memory dump from qemu-kvm-rhev core)

* Tue Mar 10 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.2.0-7.el7
- kvm-aarch64-Add-PCI-and-VIRTIO_PCI-devices-for-AArch64.patch [bz#1200090]
- kvm-Add-specific-config-options-for-PCI-E-bridges.patch [bz#1200090]
- Resolves: bz#1200090
  (qemu-kvm-rhev (2.2.0-6) breaks ISO installation)

* Mon Mar 02 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.2.0-6.el7
- kvm-AArch64-Prune-the-devices-available-for-AArch64-gues.patch [bz#1170734]
- kvm-Give-ivshmem-its-own-config-option.patch [bz#1170734]
- kvm-aarch64-Prune-unsupported-CPU-types-for-aarch64.patch [bz#1170734]
- Resolves: bz#1170734
  (Trim qemu-kvm devices for aarch64)

* Wed Feb 11 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.2.0-5.el7
- kvm-kvm_stat-Add-aarch64-support.patch [bz#1184603]
- kvm-kvm_stat-Update-exit-reasons-to-the-latest-defintion.patch [bz#1184603]
- kvm-kvm_stat-Add-RESET-support-for-perf-event-ioctl.patch [bz#1184603]
- kvm-ignore-SIGIO-in-tests-that-use-AIO-context-aarch64-h.patch [bz#1184405]
- kvm-aio_notify-force-main-loop-wakeup-with-SIGIO-aarch64.patch [bz#1184405]
- Resolves: bz#1184405
  (lost block IO completion notification (for virtio-scsi disk) hangs main loop)
- Resolves: bz#1184603
  (enable kvm_stat support for aarch64)

* Mon Feb 09 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.2.0-4.el7
- kvm-Downstream-only-Restore-pseries-machine-alias.patch [bz#1170934]
- kvm-PPC-Fix-crash-on-spapr_tce_table_finalize.patch [bz#1170934]
- kvm-virtio_serial-Don-t-use-vser-config.max_nr_ports-int.patch [bz#1169230]
- kvm-virtio-serial-Don-t-keep-a-persistent-copy-of-config.patch [bz#1169230]
- kvm-spapr-Fix-stale-HTAB-during-live-migration-KVM.patch [bz#1168446]
- kvm-spapr-Fix-integer-overflow-during-migration-TCG.patch [bz#1168446]
- kvm-spapr-Fix-stale-HTAB-during-live-migration-TCG.patch [bz#1168446]
- Resolves: bz#1168446
  (Stale hash PTEs may be transferred during live migration of PAPR guests)
- Resolves: bz#1169230
  (QEMU core dumped when do ping-pong migration to file for LE guest)
- Resolves: bz#1170934
  (Segfault at spapr_tce_table_finalize(): QLIST_REMOVE(tcet, list))

* Thu Jan 22 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.2.0-3.el7
- kvm-Downstream-only-arm-define-a-new-machine-type-for-RH.patch [bz#1176838]
- Resolves: bz#1176838
  (create rhelsa machine type)

* Wed Jan 14 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.2.0-2.el7.next.candidate
- kvm-Update-to-qemu-kvm-rhev-2.1.2-19.el7.patch []
- kvm-fw_cfg-remove-superfluous-blank-line.patch [bz#1169869]
- kvm-hw-arm-boot-fix-uninitialized-scalar-variable-warnin.patch [bz#1169869]
- kvm-Sort-include-qemu-typedefs.h.patch [bz#1169869]
- kvm-fw_cfg-hard-separation-between-the-MMIO-and-I-O-port.patch [bz#1169869]
- kvm-fw_cfg-move-boards-to-fw_cfg_init_io-fw_cfg_init_mem.patch [bz#1169869]
- kvm-fw_cfg_mem-max-access-size-and-region-size-are-the-s.patch [bz#1169869]
- kvm-fw_cfg_mem-flip-ctl_mem_ops-and-data_mem_ops-to-DEVI.patch [bz#1169869]
- kvm-exec-allows-8-byte-accesses-in-subpage_ops.patch [bz#1169869]
- kvm-fw_cfg_mem-introduce-the-data_width-property.patch [bz#1169869]
- kvm-fw_cfg_mem-expose-the-data_width-property-with-fw_cf.patch [bz#1169869]
- kvm-arm-add-fw_cfg-to-virt-board.patch [bz#1169869]
- kvm-hw-loader-split-out-load_image_gzipped_buffer.patch [bz#1169869]
- kvm-hw-arm-pass-pristine-kernel-image-to-guest-firmware-.patch [bz#1169869]
- kvm-hw-arm-virt-enable-passing-of-EFI-stubbed-kernel-to-.patch [bz#1169869]
- kvm-fw_cfg-fix-endianness-in-fw_cfg_data_mem_read-_write.patch [bz#1169869]
- Resolves: bz#1169869
  (add fw_cfg to mach-virt)

* Tue Jan 13 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-19.el7
- kvm-smbios-Fix-dimm-size-calculation-when-RAM-is-multipl.patch [bz#1179165]
- kvm-smbios-Don-t-report-unknown-CPU-speed-fix-SVVP-regre.patch [bz#1177127]
- Resolves: bz#1177127
  ([SVVP]smbios HCT job failed with  'Processor Max Speed cannot be Unknown' with -M pc-i440fx-rhel7.1.0)
- Resolves: bz#1179165
  ([SVVP]smbios HCT job failed with  Unspecified error  with -M pc-i440fx-rhel7.1.0)

* Thu Jan 08 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.2.0-1.el7
- rebase to qemu 2.2.0

* Thu Jan 08 2015 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-18.el7
- kvm-vl-Adjust-the-place-of-calling-mlockall-to-speedup-V.patch [bz#1173394]
- kvm-block-delete-cow-block-driver.patch [bz#1175841]
- Resolves: bz#1173394
  (numa_smaps doesn't respect bind policy with huge page)
- Resolves: bz#1175841
  (Delete cow block driver)

* Tue Dec 16 2014 Jeff E. Nelson <jen@redhat.com> - rhev-2.1.2-17.el7
- kvm-numa-Don-t-allow-memdev-on-RHEL-6-machine-types.patch [bz#1170093]
- kvm-block-allow-bdrv_unref-to-be-passed-NULL-pointers.patch [bz#1136381]
- kvm-block-vdi-use-block-layer-ops-in-vdi_create-instead-.patch [bz#1136381]
- kvm-block-use-the-standard-ret-instead-of-result.patch [bz#1136381]
- kvm-block-vpc-use-block-layer-ops-in-vpc_create-instead-.patch [bz#1136381]
- kvm-block-iotest-update-084-to-test-static-VDI-image-cre.patch [bz#1136381]
- kvm-block-remove-BLOCK_OPT_NOCOW-from-vdi_create_opts.patch [bz#1136381]
- kvm-block-remove-BLOCK_OPT_NOCOW-from-vpc_create_opts.patch [bz#1136381]
- kvm-migration-fix-parameter-validation-on-ram-load-CVE-2.patch [bz#1163079]
- kvm-qdev-monitor-fix-segmentation-fault-on-qdev_device_h.patch [bz#1169280]
- kvm-block-migration-Disable-cache-invalidate-for-incomin.patch [bz#1171552]
- kvm-acpi-Use-apic_id_limit-when-calculating-legacy-ACPI-.patch [bz#1173167]
- Resolves: bz#1136381
  (RFE: Supporting creating vdi/vpc format disk with protocols (glusterfs) for qemu-kvm-rhev-2.1.x)
- Resolves: bz#1163079
  (CVE-2014-7840 qemu-kvm-rhev: qemu: insufficient parameter validation during ram load [rhel-7.1])
- Resolves: bz#1169280
  (Segfault while query device properties (ics, icp))
- Resolves: bz#1170093
  (guest NUMA failed to migrate when machine is rhel6.5.0)
- Resolves: bz#1171552
  (Storage vm migration failed when running BurnInTes)
- Resolves: bz#1173167
  (Corrupted ACPI tables in some configurations using pc-i440fx-rhel7.0.0)

* Fri Dec 05 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-16.el7
- kvm-qemu-iotests-Fix-broken-test-cases.patch [bz#1169589]
- kvm-Fix-for-crash-after-migration-in-virtio-rng-on-bi-en.patch [bz#1165087]
- kvm-Downstream-only-remove-unsupported-machines-from-AAr.patch [bz#1169847]
- Resolves: bz#1165087
  (QEMU core dumped for the destination guest when do migating guest to file)
- Resolves: bz#1169589
  (test case 051 071 and 087 of qemu-iotests fail for qcow2 with qemu-kvm-rhev-2.1.2-14.el7)
- Resolves: bz#1169847
  (only support mach-virt)

* Tue Dec 02 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-15.el7
- kvm-scsi-Optimize-scsi_req_alloc.patch [bz#1141656]
- kvm-virtio-scsi-Optimize-virtio_scsi_init_req.patch [bz#1141656]
- kvm-virtio-scsi-Fix-comment-for-VirtIOSCSIReq.patch [bz#1141656]
- kvm-Downstream-only-Move-daemon-reload-to-make-sure-new-.patch [bz#1168085]
- Resolves: bz#1141656
  (Virtio-scsi: performance degradation from 1.5.3 to 2.1.0)
- Resolves: bz#1168085
  (qemu-kvm-rhev install scripts sometimes don't recognize newly installed systemd presets)

* Thu Nov 27 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-14.el7
- kvm-xhci-add-sanity-checks-to-xhci_lookup_uport.patch [bz#1161397]
- kvm-qemu-img-Allow-source-cache-mode-specification.patch [bz#1166481]
- kvm-qemu-img-Allow-cache-mode-specification-for-amend.patch [bz#1166481]
- kvm-qemu-img-fix-img_compare-flags-error-path.patch [bz#1166481]
- kvm-qemu-img-clarify-src_cache-option-documentation.patch [bz#1166481]
- kvm-qemu-img-fix-rebase-src_cache-option-documentation.patch [bz#1166481]
- Resolves: bz#1161397
  (qemu core dump when install a RHEL.7 guest(xhci) with migration)
- Resolves: bz#1166481
  (Allow qemu-img to bypass the host cache (check, compare, convert, rebase, amend))

* Tue Nov 25 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-13.el7
- kvm-hw-pci-fixed-error-flow-in-pci_qdev_init.patch [bz#1166067]
- kvm-hw-pci-fixed-hotplug-crash-when-using-rombar-0-with-.patch [bz#1166067]
- Resolves: bz#1166067
  (qemu-kvm aborted when hot plug PCI device to guest with romfile and rombar=0)

* Fri Nov 21 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-12.el7
- kvm-migration-static-variables-will-not-be-reset-at-seco.patch [bz#1166501]
- Resolves: bz#1166501
  (Migration "expected downtime" does not refresh after reset to a new value)

* Fri Nov 21 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-11.el7
- kvm-iscsi-Refuse-to-open-as-writable-if-the-LUN-is-write.patch [bz#1160102]
- kvm-vnc-sanitize-bits_per_pixel-from-the-client.patch [bz#1157646]
- kvm-usb-host-fix-usb_host_speed_compat-tyops.patch [bz#1160504]
- kvm-block-raw-posix-Fix-disk-corruption-in-try_fiemap.patch [bz#1142331]
- kvm-block-raw-posix-use-seek_hole-ahead-of-fiemap.patch [bz#1142331]
- kvm-raw-posix-Fix-raw_co_get_block_status-after-EOF.patch [bz#1142331]
- kvm-raw-posix-raw_co_get_block_status-return-value.patch [bz#1142331]
- kvm-raw-posix-SEEK_HOLE-suffices-get-rid-of-FIEMAP.patch [bz#1142331]
- kvm-raw-posix-The-SEEK_HOLE-code-is-flawed-rewrite-it.patch [bz#1142331]
- kvm-exec-Handle-multipage-ranges-in-invalidate_and_set_d.patch [bz#1164759]
- Resolves: bz#1142331
  (qemu-img convert intermittently corrupts output images)
- Resolves: bz#1157646
  (CVE-2014-7815 qemu-kvm-rhev: qemu: vnc: insufficient bits_per_pixel from the client sanitization [rhel-7.1])
- Resolves: bz#1160102
  (opening read-only iscsi lun as read-write should fail)
- Resolves: bz#1160504
  (guest can not show usb device after adding some usb controllers and redirdevs.)
- Resolves: bz#1164759
  (Handle multipage ranges in invalidate_and_set_dirty())

* Thu Nov 20 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-10.el7
- kvm-pc-dimm-Don-t-check-dimm-node-when-there-is-non-NUMA.patch [bz#1150510 bz#1163735]
- kvm-vga-Start-cutting-out-non-32bpp-conversion-support.patch [bz#1146809]
- kvm-vga-Remove-remainder-of-old-conversion-cruft.patch [bz#1146809]
- kvm-vga-Separate-LE-and-BE-conversion-functions.patch [bz#1146809]
- kvm-vga-Remove-rgb_to_pixel-indirection.patch [bz#1146809]
- kvm-vga-Simplify-vga_draw_blank-a-bit.patch [bz#1146809]
- kvm-cirrus-Remove-non-32bpp-cursor-drawing.patch [bz#1146809]
- kvm-vga-Remove-some-should-be-done-in-BIOS-comments.patch [bz#1146809]
- kvm-vga-Rename-vga_template.h-to-vga-helpers.h.patch [bz#1146809]
- kvm-vga-Make-fb-endian-a-common-state-variable.patch [bz#1146809]
- kvm-vga-Add-endian-to-vmstate.patch [bz#1146809]
- kvm-vga-pci-add-qext-region-to-mmio.patch [bz#1146809]
- kvm-virtio-scsi-work-around-bug-in-old-BIOSes.patch [bz#1123812]
- kvm-Revert-Downstream-only-Add-script-to-autoload-KVM-mo.patch [bz#1158250 bz#1159706]
- kvm-Downstream-only-add-script-on-powerpc-to-configure-C.patch [bz#1158250 bz#1158251 bz#1159706]
- kvm-block-New-bdrv_nb_sectors.patch [bz#1132385]
- kvm-vmdk-Optimize-cluster-allocation.patch [bz#1132385]
- kvm-vmdk-Handle-failure-for-potentially-large-allocation.patch [bz#1132385]
- kvm-vmdk-Use-bdrv_nb_sectors-where-sectors-not-bytes-are.patch [bz#1132385]
- kvm-vmdk-fix-vmdk_parse_extents-extent_file-leaks.patch [bz#1132385]
- kvm-vmdk-fix-buf-leak-in-vmdk_parse_extents.patch [bz#1132385]
- kvm-vmdk-Fix-integer-overflow-in-offset-calculation.patch [bz#1132385]
- kvm-Revert-Build-ceph-rbd-only-for-rhev.patch [bz#1140744]
- kvm-Revert-rbd-Only-look-for-qemu-specific-copy-of-librb.patch [bz#1140744]
- kvm-Revert-rbd-link-and-load-librbd-dynamically.patch [bz#1140744]
- kvm-spec-Enable-rbd-driver-add-dependency.patch [bz#1140744]
- kvm-Use-qemu-kvm-in-documentation-instead-of-qemu-system.patch [bz#1140620]
- kvm-ide-stash-aiocb-for-flushes.patch [bz#1024599]
- kvm-ide-simplify-reset-callbacks.patch [bz#1024599]
- kvm-ide-simplify-set_inactive-callbacks.patch [bz#1024599]
- kvm-ide-simplify-async_cmd_done-callbacks.patch [bz#1024599]
- kvm-ide-simplify-start_transfer-callbacks.patch [bz#1024599]
- kvm-ide-wrap-start_dma-callback.patch [bz#1024599]
- kvm-ide-remove-wrong-setting-of-BM_STATUS_INT.patch [bz#1024599]
- kvm-ide-fold-add_status-callback-into-set_inactive.patch [bz#1024599]
- kvm-ide-move-BM_STATUS-bits-to-pci.-ch.patch [bz#1024599]
- kvm-ide-move-retry-constants-out-of-BM_STATUS_-namespace.patch [bz#1024599]
- kvm-ahci-remove-duplicate-PORT_IRQ_-constants.patch [bz#1024599]
- kvm-ide-stop-PIO-transfer-on-errors.patch [bz#1024599]
- kvm-ide-make-all-commands-go-through-cmd_done.patch [bz#1024599]
- kvm-ide-atapi-Mark-non-data-commands-as-complete.patch [bz#1024599]
- kvm-ahci-construct-PIO-Setup-FIS-for-PIO-commands.patch [bz#1024599]
- kvm-ahci-properly-shadow-the-TFD-register.patch [bz#1024599]
- kvm-ahci-Correct-PIO-D2H-FIS-responses.patch [bz#1024599]
- kvm-ahci-Update-byte-count-after-DMA-completion.patch [bz#1024599]
- kvm-ahci-Fix-byte-count-regression-for-ATAPI-PIO.patch [bz#1024599]
- kvm-ahci-Fix-SDB-FIS-Construction.patch [bz#1024599]
- kvm-vhost-user-fix-mmap-offset-calculation.patch [bz#1159710]
- Resolves: bz#1024599
  (Windows7 x86 guest with ahci backend hit BSOD when do "hibernate")
- Resolves: bz#1123812
  (Reboot guest and guest's virtio-scsi disk will be lost after forwards migration (from RHEL6.6 host to RHEL7.1 host))
- Resolves: bz#1132385
  (qemu-img convert rate about 100k/second from qcow2/raw to vmdk format on nfs system file)
- Resolves: bz#1140620
  (Should replace "qemu-system-i386" by "/usr/libexec/qemu-kvm" in manpage of qemu-kvm for our official qemu-kvm build)
- Resolves: bz#1140744
  (Enable native support for Ceph)
- Resolves: bz#1146809
  (Incorrect colours on virtual VGA with ppc64le guest under ppc64 host)
- Resolves: bz#1150510
  (kernel ignores ACPI memory devices (PNP0C80) present at boot time)
- Resolves: bz#1158250
  (KVM modules are not autoloaded on POWER hosts)
- Resolves: bz#1158251
  (POWER KVM host starts by default with threads enabled, which prevents running guests)
- Resolves: bz#1159706
  (Need means to configure subcore mode for RHEL POWER8 hosts)
- Resolves: bz#1159710
  (vhost-user:Bad ram offset)
- Resolves: bz#1163735
  (-device pc-dimm fails to initialize on non-NUMA configs)

* Wed Nov 19 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-9.el7
- kvm-aarch64-raise-max_cpus-to-8.patch [bz#1160325]
- kvm-hw-arm-virt-add-linux-stdout-path-to-chosen-DT-node.patch [bz#1160325]
- kvm-hw-arm-virt-Provide-flash-devices-for-boot-ROMs.patch [bz#1160325]
- kvm-hw-arm-boot-load-DTB-as-a-ROM-image.patch [bz#1160325]
- kvm-hw-arm-boot-pass-an-address-limit-to-and-return-size.patch [bz#1160325]
- kvm-hw-arm-boot-load-device-tree-to-base-of-DRAM-if-no-k.patch [bz#1160325]
- kvm-hw-arm-boot-enable-DTB-support-when-booting-ELF-imag.patch [bz#1160325]
- kvm-hw-arm-virt-mark-timer-in-fdt-as-v8-compatible.patch [bz#1160325]
- kvm-hw-arm-boot-register-cpu-reset-handlers-if-using-bio.patch [bz#1160325]
- kvm-Downstream-only-Declare-ARM-kernel-support-read-only.patch [bz#1160325]
- Resolves: bz#1160325
  (arm64: support aavmf)

* Thu Nov 13 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-8.el7
- kvm-ide-Add-wwn-support-to-IDE-ATAPI-drive.patch [bz#1150820]
- kvm-exec-report-error-when-memory-hpagesize.patch [bz#1147354]
- kvm-exec-add-parameter-errp-to-gethugepagesize.patch [bz#1147354]
- kvm-block-curl-Improve-type-safety-of-s-timeout.patch [bz#1152901]
- kvm-virtio-serial-avoid-crash-when-port-has-no-name.patch [bz#1151947]
- Resolves: bz#1147354
  (Qemu core dump when boot up a guest on a non-existent hugepage path)
- Resolves: bz#1150820
  (fail to specify wwn for virtual IDE CD-ROM)
- Resolves: bz#1151947
  (virtconsole causes qemu-kvm core dump)
- Resolves: bz#1152901
  (block/curl: Fix type safety of s->timeout)

* Thu Nov 06 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-7.el7
- kvm-ac97-register-reset-via-qom.patch [bz#1141666]
- kvm-specfile-Require-glusterfs-api-3.6.patch [bz#1157329]
- kvm-smbios-Fix-assertion-on-socket-count-calculation.patch [bz#1146573]
- kvm-smbios-Encode-UUID-according-to-SMBIOS-specification.patch [bz#1152922]
- kvm-virtio-scsi-Report-error-if-num_queues-is-0-or-too-l.patch [bz#1146826]
- kvm-virtio-scsi-Fix-memory-leak-when-realize-failed.patch [bz#1146826]
- kvm-virtio-scsi-Fix-num_queue-input-validation.patch [bz#1146826]
- kvm-util-Improve-os_mem_prealloc-error-message.patch [bz#1153590]
- kvm-Downstream-only-Add-script-to-autoload-KVM-modules-o.patch [bz#1158250]
- kvm-Downstream-only-remove-uneeded-PCI-devices-for-POWER.patch [bz#1160120]
- kvm-Downstream-only-Remove-assorted-unneeded-devices-for.patch [bz#1160120]
- kvm-Downstream-only-Remove-ISA-bus-and-device-support-fo.patch [bz#1160120]
- kvm-well-defined-listing-order-for-machine-types.patch [bz#1145042]
- kvm-i386-pc-add-piix-and-q35-machtypes-to-sorting-famili.patch [bz#1145042]
- kvm-i386-pc-add-RHEL-machtypes-to-sorting-families-for-M.patch [bz#1145042]
- Resolves: bz#1141666
  (Qemu crashed if reboot guest after hot remove AC97 sound device)
- Resolves: bz#1145042
  (The output of "/usr/libexec/qemu-kvm -M ?" should be ordered.)
- Resolves: bz#1146573
  (qemu core dump when boot guest with smp(num)<cores(num))
- Resolves: bz#1146826
  (QEMU will not reject invalid number of queues (num_queues = 0) specified for virtio-scsi)
- Resolves: bz#1152922
  (smbios uuid mismatched)
- Resolves: bz#1153590
  (Improve error message on huge page preallocation)
- Resolves: bz#1157329
  (qemu-kvm: undefined symbol: glfs_discard_async)
- Resolves: bz#1158250
  (KVM modules are not autoloaded on POWER hosts)
- Resolves: bz#1160120
  (qemu-kvm-rhev shouldn't include non supported devices for POWER)

* Tue Nov 04 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-6.el7
- kvm-ivshmem-use-error_report.patch [bz#1104063]
- kvm-ivshmem-RHEL-only-remove-unsupported-code.patch [bz#1104063]
- kvm-ivshmem-RHEL-only-explicitly-remove-dead-code.patch [bz#1104063]
- kvm-Revert-rhel-Drop-ivshmem-device.patch [bz#1104063]
- kvm-serial-reset-state-at-startup.patch [bz#1135844]
- kvm-spice-call-qemu_spice_set_passwd-during-init.patch [bz#1140975]
- kvm-input-fix-send-key-monitor-command-release-event-ord.patch [bz#1145028 bz#1146801]
- kvm-virtio-scsi-sense-in-virtio_scsi_command_complete.patch [bz#1152830]
- Resolves: bz#1104063
  ([RHEL7.1 Feat] Enable qemu-kvm Inter VM Shared Memory (IVSHM) feature)
- Resolves: bz#1135844
  ([virtio-win]communication ports were marked with a  yellow exclamation after hotplug pci-serial,pci-serial-2x,pci-serial-4x)
- Resolves: bz#1140975
  (fail to login spice session with password + expire time)
- Resolves: bz#1145028
  (send-key does not crash windows guest even when it should)
- Resolves: bz#1146801
  (sendkey: releasing order of combined keys was wrongly converse)
- Resolves: bz#1152830
  (Fix sense buffer in virtio-scsi LUN passthrough)

* Fri Oct 24 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-5.el7
- kvm-blockdev-Orphaned-drive-search.patch [bz#946993]
- kvm-blockdev-Allow-overriding-if_max_dev-property.patch [bz#946993]
- kvm-pc-vl-Add-units-per-default-bus-property.patch [bz#946993]
- kvm-ide-Update-ide_drive_get-to-be-HBA-agnostic.patch [bz#946993]
- kvm-qtest-bios-tables-Correct-Q35-command-line.patch [bz#946993]
- kvm-q35-ahci-Pick-up-cdrom-and-hda-options.patch [bz#946993]
- kvm-trace-events-drop-orphan-virtio_blk_data_plane_compl.patch [bz#1144325]
- kvm-trace-events-drop-orphan-usb_mtp_data_out.patch [bz#1144325]
- kvm-trace-events-drop-orphan-iscsi-trace-events.patch [bz#1144325]
- kvm-cleanup-trace-events.pl-Tighten-search-for-trace-eve.patch [bz#1144325]
- kvm-trace-events-Drop-unused-megasas-trace-event.patch [bz#1144325]
- kvm-trace-events-Drop-orphaned-monitor-trace-event.patch [bz#1144325]
- kvm-trace-events-Fix-comments-pointing-to-source-files.patch [bz#1144325]
- kvm-simpletrace-add-simpletrace.py-no-header-option.patch [bz#1155015]
- kvm-trace-extract-stap_escape-function-for-reuse.patch [bz#1155015]
- kvm-trace-add-tracetool-simpletrace_stap-format.patch [bz#1155015]
- kvm-trace-install-simpletrace-SystemTap-tapset.patch [bz#1155015]
- kvm-trace-install-trace-events-file.patch [bz#1155015]
- kvm-trace-add-SystemTap-init-scripts-for-simpletrace-bri.patch [bz#1155015]
- kvm-simpletrace-install-simpletrace.py.patch [bz#1155015]
- kvm-trace-add-systemtap-initscript-README-file-to-RPM.patch [bz#1155015]
- Resolves: bz#1144325
  (Can not probe  "qemu.kvm.virtio_blk_data_plane_complete_request")
- Resolves: bz#1155015
  ([Fujitsu 7.1 FEAT]:QEMU: capturing trace data all the time using ftrace-based tracing)
- Resolves: bz#946993
  (Q35 does not honor -drive if=ide,... and its sugared forms -cdrom, -hda, ...)

* Mon Oct 20 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-4.el7
- kvm-seccomp-add-semctl-to-the-syscall-whitelist.patch [bz#1126704]
- kvm-dataplane-fix-virtio_blk_data_plane_create-op-blocke.patch [bz#1140001]
- kvm-block-fix-overlapping-multiwrite-requests.patch [bz#1123908]
- kvm-qemu-iotests-add-multiwrite-test-cases.patch [bz#1123908]
- Resolves: bz#1123908
  (block.c: multiwrite_merge() truncates overlapping requests)
- Resolves: bz#1126704
  (BUG: When use '-sandbox on'+'vnc'+'hda' and quit, qemu-kvm hang)
- Resolves: bz#1140001
  (data-plane hotplug should be refused to start if device is already in use (drive-mirror job))

* Fri Oct 10 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-3.el7
- kvm-Disable-tests-for-removed-features.patch [bz#1108040]
- kvm-Disable-arm-board-types-using-lsi53c895a.patch [bz#1108040]
- kvm-libqtest-launch-QEMU-with-QEMU_AUDIO_DRV-none.patch [bz#1108040]
- kvm-Whitelist-blkdebug-driver.patch [bz#1108040]
- kvm-Turn-make-check-on.patch [bz#1108040]
- Resolves: bz#1108040
  (Enable make check for qemu-kvm-rhev 2.0 and newer)

* Fri Oct 10 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-2.el7
- kvm-RPM-spec-Add-enable-numa-to-configure-command-line.patch [bz#1076990]
- kvm-block.curl-adding-timeout-option.patch [bz#1132569]
- kvm-curl-Allow-a-cookie-or-cookies-to-be-sent-with-http-.patch [bz#1132569]
- kvm-curl-Don-t-deref-NULL-pointer-in-call-to-aio_poll.patch [bz#1132569]
- kvm-curl-Add-timeout-and-cookie-options-and-misc.-fix-RH.patch [bz#1132569]
- kvm-Introduce-cpu_clean_all_dirty.patch [bz#1143054]
- kvm-kvmclock-Ensure-proper-env-tsc-value-for-kvmclock_cu.patch [bz#1143054]
- kvm-kvmclock-Ensure-time-in-migration-never-goes-backwar.patch [bz#1143054]
- kvm-IDE-Fill-the-IDENTIFY-request-consistently.patch [bz#852348]
- kvm-ide-Add-resize-callback-to-ide-core.patch [bz#852348]
- kvm-virtio-balloon-fix-integer-overflow-in-memory-stats-.patch [bz#1140997]
- kvm-block-extend-BLOCK_IO_ERROR-event-with-nospace-indic.patch [bz#1117445]
- kvm-block-extend-BLOCK_IO_ERROR-with-reason-string.patch [bz#1117445]
- Resolves: bz#1076990
  (Enable complex memory requirements for virtual machines)
- Resolves: bz#1117445
  (QMP: extend block events with error information)
- Resolves: bz#1132569
  (RFE: Enable curl driver in qemu-kvm-rhev: https only)
- Resolves: bz#1140997
  (guest is stuck when setting balloon memory with large guest-stats-polling-interval)
- Resolves: bz#1143054
  (kvmclock: Ensure time in migration never goes backward (backport))
- Resolves: bz#852348
  (fail to block_resize local data disk with IDE/AHCI disk_interface)

* Fri Sep 26 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.2-1.el7
- Rebase to qemu 2.1.2 [bz#1121609]
- Resolves: bz#1121609
  Rebase qemu-kvm-rhev to qemu 2.1.2

* Wed Sep 24 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.0-5.el7
- kvm-target-i386-Reject-invalid-CPU-feature-names-on-the-.patch [bz#1055532]
- kvm-target-ppc-virtex-ml507-machine-type-should-depend-o.patch [bz#1113998]
- kvm-RHEL-only-Disable-tests-that-don-t-work-with-RHEL-bu.patch [bz#1113998]
- kvm-RHEL-onlyy-Disable-unused-ppc-machine-types.patch [bz#1113998]
- kvm-RHEL-only-Remove-unneeded-devices-from-ppc64-qemu-kv.patch []
- kvm-RHEL-only-Replace-upstream-pseries-machine-types-wit.patch []
- kvm-scsi-bus-prepare-scsi_req_new-for-introduction-of-pa.patch [bz#1123349]
- kvm-scsi-bus-introduce-parse_cdb-in-SCSIDeviceClass-and-.patch [bz#1123349]
- kvm-scsi-block-extract-scsi_block_is_passthrough.patch [bz#1123349]
- kvm-scsi-block-scsi-generic-implement-parse_cdb.patch [bz#1123349]
- kvm-virtio-scsi-implement-parse_cdb.patch [bz#1123349]
- kvm-exec-file_ram_alloc-print-error-when-prealloc-fails.patch [bz#1135893]
- kvm-pc-increase-maximal-VCPU-count-to-240.patch [bz#1144089]
- kvm-ssh-Enable-ssh-driver-in-qemu-kvm-rhev-RHBZ-1138359.patch [bz#1138359]
- Resolves: bz#1055532
  (QEMU should abort when invalid CPU flag name is used)
- Resolves: bz#1113998
  (RHEL Power/KVM (qemu-kvm-rhev))
- Resolves: bz#1123349
  ([FJ7.0 Bug] SCSI command issued from KVM guest doesn't reach target device)
- Resolves: bz#1135893
  (qemu-kvm should report an error message when host's freehugepage memory < domain's memory)
- Resolves: bz#1138359
  (RFE: Enable ssh driver in qemu-kvm-rhev)
- Resolves: bz#1144089
  ([HP 7.1 FEAT] Increase qemu-kvm-rhev's VCPU limit to 240)

* Wed Sep 17 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.0-4.el7
- kvm-virtio-rng-add-some-trace-events.patch [bz#1129259]
- kvm-block-vhdx-add-error-check.patch [bz#1126976]
- kvm-block-VHDX-endian-fixes.patch [bz#1126976]
- kvm-qdev-monitor-include-QOM-properties-in-device-FOO-he.patch [bz#1133736]
- kvm-block-acquire-AioContext-in-qmp_block_resize.patch [bz#1136752]
- kvm-virtio-blk-allow-block_resize-with-dataplane.patch [bz#1136752]
- kvm-block-acquire-AioContext-in-do_drive_del.patch [bz#1136752]
- kvm-virtio-blk-allow-drive_del-with-dataplane.patch [bz#1136752]
- kvm-rhel-Add-rhel7.1.0-machine-types.patch [bz#1093023]
- kvm-vmstate_xhci_event-bug-compat-for-rhel7.0.0-machine-.patch [bz#1136512]
- kvm-pflash_cfi01-fixup-stale-DPRINTF-calls.patch [bz#1139706]
- kvm-pflash_cfi01-write-flash-contents-to-bdrv-on-incomin.patch [bz#1139706]
- kvm-ide-Fix-segfault-when-flushing-a-device-that-doesn-t.patch [bz#1140145]
- kvm-xhci-PCIe-endpoint-migration-compatibility-fix.patch [bz#1138579]
- kvm-rh-machine-types-xhci-PCIe-endpoint-migration-compat.patch [bz#1138579]
- Resolves: bz#1093023
  (provide RHEL-specific machine types in QEMU)
- Resolves: bz#1126976
  (VHDX image format does not work on PPC64 (Endian issues))
- Resolves: bz#1129259
  (Add traces to virtio-rng device)
- Resolves: bz#1133736
  (qemu should provide iothread and x-data-plane properties for /usr/libexec/qemu-kvm -device virtio-blk-pci,?)
- Resolves: bz#1136512
  (rhel7.0.0 machtype compat after CVE-2014-5263 vmstate_xhci_event: fix unterminated field list)
- Resolves: bz#1136752
  (virtio-blk dataplane support for block_resize and hot unplug)
- Resolves: bz#1138579
  (Migration failed with nec-usb-xhci from RHEL7. 0 to RHEL7.1)
- Resolves: bz#1139706
  (pflash (UEFI varstore) migration shortcut for libvirt [RHEV])
- Resolves: bz#1140145
  (qemu-kvm crashed when doing iofuzz testing)

* Thu Aug 28 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.0-3.el7
- kvm-Fix-pkgversion-value.patch [bz#1064742]
- kvm-virtio-serial-create-a-linked-list-of-all-active-dev.patch [bz#1003432]
- kvm-virtio-serial-search-for-duplicate-port-names-before.patch [bz#1003432]
- kvm-pc-RHEL-6-CPUID-compat-code-for-Broadwell-CPU-model.patch [bz#1111351]
- kvm-rpm-spec-build-qemu-kvm-with-lzo-and-snappy-enabled.patch [bz#1126933]
- Resolves: bz#1003432
  (qemu-kvm should not allow different virtio serial port use the same name)
- Resolves: bz#1064742
  (QMP: "query-version" doesn't include the -rhev prefix from the qemu-kvm-rhev package)
- Resolves: bz#1111351
  (RHEL-6.6 migration compatibility: CPU models)
- Resolves: bz#1126933
  ([FEAT RHEV7.1]: qemu: Support compression for dump-guest-memory command)

* Mon Aug 18 2014 Miroslav Rezanina <> - rhev-2.1.0-2.el7
- kvm-exit-when-no-kvm-and-vcpu-count-160.patch [bz#1076326 bz#1118665]
- kvm-Revert-Use-legacy-SMBIOS-for-rhel-machine-types.patch [bz#1118665]
- kvm-rhel-Use-SMBIOS-legacy-mode-for-machine-types-7.0.patch [bz#1118665]
- kvm-rhel-Suppress-hotplug-memory-address-space-for-machi.patch [bz#1118665]
- kvm-rhel-Fix-ACPI-table-size-for-machine-types-7.0.patch [bz#1118665]
- kvm-rhel-Fix-missing-pc-q35-rhel7.0.0-compatibility-prop.patch [bz#1118665]
- kvm-rhel-virtio-scsi-pci.any_layout-off-for-machine-type.patch [bz#1118665]
- kvm-rhel-PIIX4_PM.memory-hotplug-support-off-for-machine.patch [bz#1118665]
- kvm-rhel-apic.version-0x11-for-machine-types-7.0.patch [bz#1118665]
- kvm-rhel-nec-usb-xhci.superspeed-ports-first-off-for-mac.patch [bz#1118665]
- kvm-rhel-pci-serial.prog_if-0-for-machine-types-7.0.patch [bz#1118665]
- kvm-rhel-virtio-net-pci.guest_announce-off-for-machine-t.patch [bz#1118665]
- kvm-rhel-ICH9-LPC.memory-hotplug-support-off-for-machine.patch [bz#1118665]
- kvm-rhel-.power_controller_present-off-for-machine-types.patch [bz#1118665]
- kvm-rhel-virtio-net-pci.ctrl_guest_offloads-off-for-mach.patch [bz#1118665]
- kvm-pc-q35-rhel7.0.0-Disable-x2apic-default.patch [bz#1118665]
- Resolves: bz#1076326
  (qemu-kvm does not quit when booting guest w/ 161 vcpus and "-no-kvm")
- Resolves: bz#1118665
  (Migration: rhel7.0->rhev7.1)

* Sat Aug 02 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.1.0-1.el7
- Rebase to 2.1.0 [bz#1121609]
- Resolves: bz#1121609
 (Rebase qemu-kvm-rhev to qemu 2.1)

* Wed Jul 09 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.0.0-3.el7
- kvm-Remove-CONFIG_NE2000_ISA-from-all-config-files.patch []
- kvm-Fix-conditional-rpmbuild.patch []
- kvm-RHEL7-RHEV7.1-2.0-migration-compatibility.patch [bz#1085950]
- kvm-remove-superfluous-.hot_add_cpu-and-.max_cpus-initia.patch [bz#1085950]
- kvm-set-model-in-PC_RHEL6_5_COMPAT-for-qemu32-VCPU-RHEV-.patch [bz#1085950]
- kvm-Undo-Enable-x2apic-by-default-for-compatibility.patch [bz#1085950]
- kvm-qemu_loadvm_state-shadow-SeaBIOS-for-VM-incoming-fro.patch [bz#1103579]
- Resolves: bz#1085950
  (Migration/virtio-net: 7.0->vp-2.0-rc2: Mix of migration issues)
- Resolves: bz#1103579
  (fail to reboot guest after migration from RHEL6.5 host to RHEL7.0 host)

* Fri May 30 2014 Miroslav Rezanina <mrezanin@redhat.com> - rhev-2.0.0-2.el7
- kvm-pc-add-hot_add_cpu-callback-to-all-machine-types.patch [bz#1093411]
- Resolves: bz#1093411
  (Hot unplug CPU not working for RHEL7 host)

* Fri Apr 18 2014 Miroslav Rezanina <mrezanin@redhat.com> - 2.0.0-1.el7ev
- Rebase to qemu 2.0.0

* Wed Apr 02 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-60.el7
- kvm-qcow2-fix-dangling-refcount-table-entry.patch [bz#1081793]
- kvm-qcow2-link-all-L2-meta-updates-in-preallocate.patch [bz#1081393]
- Resolves: bz#1081393
  (qemu-img will prompt that 'leaked clusters were found' while creating images with '-o preallocation=metadata,cluster_size<=1024')
- Resolves: bz#1081793
  (qemu-img core dumped when creating a qcow2 image base on block device(iscsi or libiscsi))

* Wed Mar 26 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-59.el7
- kvm-qemu-iotests-add-.-check-cloop-support.patch [bz#1066691]
- kvm-qemu-iotests-add-cloop-input-validation-tests.patch [bz#1066691]
- kvm-block-cloop-validate-block_size-header-field-CVE-201.patch [bz#1079455]
- kvm-block-cloop-prevent-offsets_size-integer-overflow-CV.patch [bz#1079320]
- kvm-block-cloop-refuse-images-with-huge-offsets-arrays-C.patch [bz#1079455]
- kvm-block-cloop-refuse-images-with-bogus-offsets-CVE-201.patch [bz#1079455]
- kvm-size-off-by-one.patch [bz#1066691]
- kvm-qemu-iotests-Support-for-bochs-format.patch [bz#1066691]
- kvm-bochs-Unify-header-structs-and-make-them-QEMU_PACKED.patch [bz#1066691]
- kvm-bochs-Use-unsigned-variables-for-offsets-and-sizes-C.patch [bz#1079339]
- kvm-bochs-Check-catalog_size-header-field-CVE-2014-0143.patch [bz#1079320]
- kvm-bochs-Check-extent_size-header-field-CVE-2014-0142.patch [bz#1079315]
- kvm-bochs-Fix-bitmap-offset-calculation.patch [bz#1066691]
- kvm-vpc-vhd-add-bounds-check-for-max_table_entries-and-b.patch [bz#1079455]
- kvm-vpc-Validate-block-size-CVE-2014-0142.patch [bz#1079315]
- kvm-vdi-add-bounds-checks-for-blocks_in_image-and-disk_s.patch [bz#1079455]
- kvm-vhdx-Bounds-checking-for-block_size-and-logical_sect.patch [bz#1079346]
- kvm-curl-check-data-size-before-memcpy-to-local-buffer.-.patch [bz#1079455]
- kvm-qcow2-Check-header_length-CVE-2014-0144.patch [bz#1079455]
- kvm-qcow2-Check-backing_file_offset-CVE-2014-0144.patch [bz#1079455]
- kvm-qcow2-Check-refcount-table-size-CVE-2014-0144.patch [bz#1079455]
- kvm-qcow2-Validate-refcount-table-offset.patch [bz#1066691]
- kvm-qcow2-Validate-snapshot-table-offset-size-CVE-2014-0.patch [bz#1079455]
- kvm-qcow2-Validate-active-L1-table-offset-and-size-CVE-2.patch [bz#1079455]
- kvm-qcow2-Fix-backing-file-name-length-check.patch [bz#1066691]
- kvm-qcow2-Don-t-rely-on-free_cluster_index-in-alloc_refc.patch [bz#1079339]
- kvm-qcow2-Avoid-integer-overflow-in-get_refcount-CVE-201.patch [bz#1079320]
- kvm-qcow2-Check-new-refcount-table-size-on-growth.patch [bz#1066691]
- kvm-qcow2-Fix-types-in-qcow2_alloc_clusters-and-alloc_cl.patch [bz#1066691]
- kvm-qcow2-Protect-against-some-integer-overflows-in-bdrv.patch [bz#1066691]
- kvm-qcow2-Fix-new-L1-table-size-check-CVE-2014-0143.patch [bz#1079320]
- kvm-dmg-coding-style-and-indentation-cleanup.patch [bz#1066691]
- kvm-dmg-prevent-out-of-bounds-array-access-on-terminator.patch [bz#1066691]
- kvm-dmg-drop-broken-bdrv_pread-loop.patch [bz#1066691]
- kvm-dmg-use-appropriate-types-when-reading-chunks.patch [bz#1066691]
- kvm-dmg-sanitize-chunk-length-and-sectorcount-CVE-2014-0.patch [bz#1079325]
- kvm-dmg-use-uint64_t-consistently-for-sectors-and-length.patch [bz#1066691]
- kvm-dmg-prevent-chunk-buffer-overflow-CVE-2014-0145.patch [bz#1079325]
- kvm-block-vdi-bounds-check-qemu-io-tests.patch [bz#1066691]
- kvm-block-Limit-request-size-CVE-2014-0143.patch [bz#1079320]
- kvm-qcow2-Fix-copy_sectors-with-VM-state.patch [bz#1066691]
- kvm-qcow2-Fix-NULL-dereference-in-qcow2_open-error-path-.patch [bz#1079333]
- kvm-qcow2-Fix-L1-allocation-size-in-qcow2_snapshot_load_.patch [bz#1079325]
- kvm-qcow2-Check-maximum-L1-size-in-qcow2_snapshot_load_t.patch [bz#1079320]
- kvm-qcow2-Limit-snapshot-table-size.patch [bz#1066691]
- kvm-parallels-Fix-catalog-size-integer-overflow-CVE-2014.patch [bz#1079320]
- kvm-parallels-Sanity-check-for-s-tracks-CVE-2014-0142.patch [bz#1079315]
- kvm-fix-machine-check-propagation.patch [bz#740107]
- Resolves: bz#1066691
  (qemu-kvm: include leftover patches from block layer security audit)
- Resolves: bz#1079315
  (CVE-2014-0142 qemu-kvm: qemu: crash by possible division by zero [rhel-7.0])
- Resolves: bz#1079320
  (CVE-2014-0143 qemu-kvm: Qemu: block: multiple integer overflow flaws [rhel-7.0])
- Resolves: bz#1079325
  (CVE-2014-0145 qemu-kvm: Qemu: prevent possible buffer overflows [rhel-7.0])
- Resolves: bz#1079333
  (CVE-2014-0146 qemu-kvm: Qemu: qcow2: NULL dereference in qcow2_open() error path [rhel-7.0])
- Resolves: bz#1079339
  (CVE-2014-0147 qemu-kvm: Qemu: block: possible crash due signed types or logic error [rhel-7.0])
- Resolves: bz#1079346
  (CVE-2014-0148 qemu-kvm: Qemu: vhdx: bounds checking for block_size and logical_sector_size [rhel-7.0])
- Resolves: bz#1079455
  (CVE-2014-0144 qemu-kvm: Qemu: block: missing input validation [rhel-7.0])
- Resolves: bz#740107
  ([Hitachi 7.0 FEAT]  KVM: MCA Recovery for KVM guest OS memory)

* Wed Mar 26 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-58.el7
- kvm-pc-Use-cpu64-rhel6-CPU-model-by-default-on-rhel6-mac.patch [bz#1080170]
- kvm-target-i386-Copy-cpu64-rhel6-definition-into-qemu64.patch [bz#1078607 bz#1080170]
- Resolves: bz#1080170
  (intel 82576 VF not work in windows 2008 x86 - Code 12 [TestOnly])
- Resolves: bz#1080170
  (Default CPU model for rhel6.* machine-types is different from RHEL-6)

* Fri Mar 21 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-57.el7
- kvm-virtio-net-fix-guest-triggerable-buffer-overrun.patch [bz#1078308]
- Resolves: bz#1078308
  (EMBARGOED CVE-2014-0150 qemu: virtio-net: fix guest-triggerable buffer overrun [rhel-7.0])

* Fri Mar 21 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-56.el7
- kvm-configure-Fix-bugs-preventing-Ceph-inclusion.patch [bz#1078809]
- Resolves: bz#1078809
  (can not boot qemu-kvm-rhev with rbd image)

* Wed Mar 19 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-55.el7
- kvm-scsi-Change-scsi-sense-buf-size-to-252.patch [bz#1058173]
- kvm-scsi-Fix-migration-of-scsi-sense-data.patch [bz#1058173]
- Resolves: bz#1058173
  (qemu-kvm core dump booting guest with scsi-generic disk attached when using built-in iscsi driver)

* Wed Mar 19 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-54.el7
- kvm-qdev-monitor-Set-properties-after-parent-is-assigned.patch [bz#1046248]
- kvm-block-Update-image-size-in-bdrv_invalidate_cache.patch [bz#1048575]
- kvm-qcow2-Keep-option-in-qcow2_invalidate_cache.patch [bz#1048575]
- kvm-qcow2-Check-bs-drv-in-copy_sectors.patch [bz#1048575]
- kvm-block-bs-drv-may-be-NULL-in-bdrv_debug_resume.patch [bz#1048575]
- kvm-iotests-Test-corruption-during-COW-request.patch [bz#1048575]
- Resolves: bz#1046248
  (qemu-kvm crash when send "info qtree" after hot plug a device with invalid addr)
- Resolves: bz#1048575
  (Segmentation fault occurs after migrate guest(use scsi disk and add stress) to des machine)

* Wed Mar 12 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-53.el7
- kvm-dataplane-Fix-startup-race.patch [bz#1069541]
- kvm-QMP-Relax-__com.redhat_drive_add-parameter-checking.patch [bz#1057471]
- kvm-all-exit-in-case-max-vcpus-exceeded.patch [bz#993429]
- kvm-block-gluster-code-movements-state-storage-changes.patch [bz#1031526]
- kvm-block-gluster-add-reopen-support.patch [bz#1031526]
- kvm-virtio-net-add-feature-bit-for-any-header-s-g.patch [bz#990989]
- kvm-spec-Add-README.rhel6-gpxe-source.patch [bz#1073774]
- kvm-pc-Add-RHEL6-e1000-gPXE-image.patch [bz#1073774]
- kvm-loader-rename-in_ram-has_mr.patch [bz#1064018]
- kvm-pc-avoid-duplicate-names-for-ROM-MRs.patch [bz#1064018]
- kvm-qemu-img-convert-Fix-progress-output.patch [bz#1073728]
- kvm-qemu-iotests-Test-progress-output-for-conversion.patch [bz#1073728]
- kvm-iscsi-Use-bs-sg-for-everything-else-than-disks.patch [bz#1067784]
- kvm-block-Fix-bs-request_alignment-assertion-for-bs-sg-1.patch [bz#1067784]
- kvm-qemu_file-use-fwrite-correctly.patch [bz#1005103]
- kvm-qemu_file-Fix-mismerge-of-use-fwrite-correctly.patch [bz#1005103]
- Resolves: bz#1005103
  (Migration should fail when migrate guest offline to a file which is specified to a readonly directory.)
- Resolves: bz#1031526
  (Can not commit snapshot when disk is using glusterfs:native backend)
- Resolves: bz#1057471
  (fail to do hot-plug with "discard = on" with "Invalid parameter 'discard'" error)
- Resolves: bz#1064018
  (abort from conflicting genroms)
- Resolves: bz#1067784
  (qemu-kvm: block.c:850: bdrv_open_common: Assertion `bs->request_alignment != 0' failed. Aborted (core dumped))
- Resolves: bz#1069541
  (Segmentation fault when boot guest with dataplane=on)
- Resolves: bz#1073728
  (progress bar doesn't display when converting with -p)
- Resolves: bz#1073774
  (e1000 ROM cause migrate fail  from RHEL6.5 host to RHEL7.0 host)
- Resolves: bz#990989
  (backport inline header virtio-net optimization)
- Resolves: bz#993429
  (kvm: test maximum number of vcpus supported (rhel7))

* Wed Mar 05 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-52.el7
- kvm-target-i386-Move-hyperv_-static-globals-to-X86CPU.patch [bz#1004773]
- kvm-Fix-uninitialized-cpuid_data.patch [bz#1057173]
- kvm-fix-coexistence-of-KVM-and-Hyper-V-leaves.patch [bz#1004773]
- kvm-make-availability-of-Hyper-V-enlightenments-depe.patch [bz#1004773]
- kvm-make-hyperv-hypercall-and-guest-os-id-MSRs-migra.patch [bz#1004773]
- kvm-make-hyperv-vapic-assist-page-migratable.patch [bz#1004773]
- kvm-target-i386-Convert-hv_relaxed-to-static-property.patch [bz#1057173]
- kvm-target-i386-Convert-hv_vapic-to-static-property.patch [bz#1057173]
- kvm-target-i386-Convert-hv_spinlocks-to-static-property.patch [bz#1057173]
- kvm-target-i386-Convert-check-and-enforce-to-static-prop.patch [bz#1004773]
- kvm-target-i386-Cleanup-foo-feature-handling.patch [bz#1057173]
- kvm-add-support-for-hyper-v-timers.patch [bz#1057173]
- Resolves: bz#1004773
  (Hyper-V guest OS id and hypercall MSRs not migrated)
- Resolves: bz#1057173
  (KVM Hyper-V Enlightenment - New feature - hv-time (QEMU))

* Wed Mar 05 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-51.el7
- kvm-qmp-access-the-local-QemuOptsLists-for-drive-option.patch [bz#1026184]
- kvm-qxl-add-sanity-check.patch [bz#751937]
- kvm-Fix-two-XBZRLE-corruption-issues.patch [bz#1063417]
- kvm-qdev-monitor-set-DeviceState-opts-before-calling-rea.patch [bz#1037956]
- kvm-vfio-blacklist-loading-of-unstable-roms.patch [bz#1037956]
- kvm-block-Set-block-filename-sizes-to-PATH_MAX-instead-o.patch [bz#1072339]
- Resolves: bz#1026184
  (QMP: querying -drive option returns a NULL parameter list)
- Resolves: bz#1037956
  (bnx2x: boot one guest to do vfio-pci with all PFs assigned in same group meet QEMU segmentation fault (Broadcom BCM57810 card))
- Resolves: bz#1063417
  (google stressapptest vs Migration)
- Resolves: bz#1072339
  (RHEV: Cannot start VMs that have more than 23 snapshots.)
- Resolves: bz#751937
  (qxl triggers assert during iofuzz test)

* Wed Feb 26 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-50.el7
- kvm-mempath-prefault-fix-off-by-one-error.patch [bz#1069039]
- kvm-qemu-option-has_help_option-and-is_valid_option_list.patch [bz#1065873]
- kvm-qemu-img-create-Support-multiple-o-options.patch [bz#1065873]
- kvm-qemu-img-convert-Support-multiple-o-options.patch [bz#1065873]
- kvm-qemu-img-amend-Support-multiple-o-options.patch [bz#1065873]
- kvm-qemu-img-Allow-o-help-with-incomplete-argument-list.patch [bz#1065873]
- kvm-qemu-iotests-Check-qemu-img-command-line-parsing.patch [bz#1065873]
- Resolves: bz#1065873
  (qemu-img silently ignores options with multiple -o parameters)
- Resolves: bz#1069039
  (-mem-prealloc option behaviour is opposite to expected)

* Wed Feb 19 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-49.el7
- kvm-xhci-add-support-for-suspend-resume.patch [bz#1012365]
- kvm-qcow2-remove-n_start-and-n_end-of-qcow2_alloc_cluste.patch [bz#1049176]
- kvm-qcow2-fix-offset-overflow-in-qcow2_alloc_clusters_at.patch [bz#1049176]
- kvm-qcow2-check-for-NULL-l2meta.patch [bz#1055848]
- kvm-qemu-iotests-add-test-for-qcow2-preallocation-with-d.patch [bz#1055848]
- Resolves: bz#1012365
  (xhci usb storage lost in guest after wakeup from S3)
- Resolves: bz#1049176
  (qemu-img core dump when using "-o preallocation=metadata,cluster_size=2048k" to create image of libiscsi lun)
- Resolves: bz#1055848
  (qemu-img core dumped when cluster size is larger than the default value with opreallocation=metadata specified)

* Mon Feb 17 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-48.el7
- kvm-spec-disable-qom-cast-debug.patch [bz#1063942]
- kvm-fix-guest-physical-bits-to-match-host-to-go-beyond-1.patch [bz#989677]
- kvm-monitor-Cleanup-mon-outbuf-on-write-error.patch [bz#1065225]
- Resolves: bz#1063942
  (configure qemu-kvm with --disable-qom-cast-debug)
- Resolves: bz#1065225
  (QMP socket breaks on unexpected close)
- Resolves: bz#989677
  ([HP 7.0 FEAT]: Increase KVM guest supported memory to 4TiB)

* Wed Feb 12 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-47.el7
- kvm-seccomp-add-mkdir-and-fchmod-to-the-whitelist.patch [bz#1026314]
- kvm-seccomp-add-some-basic-shared-memory-syscalls-to-the.patch [bz#1026314]
- kvm-scsi-Support-TEST-UNIT-READY-in-the-dummy-LUN0.patch [bz#1004143]
- kvm-usb-add-vendor-request-defines.patch [bz#1039530]
- kvm-usb-move-usb_-hi-lo-helpers-to-header-file.patch [bz#1039530]
- kvm-usb-add-support-for-microsoft-os-descriptors.patch [bz#1039530]
- kvm-usb-add-microsoft-os-descriptors-compat-property.patch [bz#1039530]
- kvm-usb-hid-add-microsoft-os-descriptor-support.patch [bz#1039530]
- kvm-configure-add-option-to-disable-fstack-protect.patch [bz#1044182]
- kvm-exec-always-use-MADV_DONTFORK.patch [bz#1004197]
- kvm-pc-Save-size-of-RAM-below-4GB.patch [bz#1048080]
- kvm-acpi-Fix-PCI-hole-handling-on-build_srat.patch [bz#1048080]
- kvm-Add-check-for-cache-size-smaller-than-page-size.patch [bz#1017096]
- kvm-XBZRLE-cache-size-should-not-be-larger-than-guest-me.patch [bz#1047448]
- kvm-Don-t-abort-on-out-of-memory-when-creating-page-cach.patch [bz#1047448]
- kvm-Don-t-abort-on-memory-allocation-error.patch [bz#1047448]
- kvm-Set-xbzrle-buffers-to-NULL-after-freeing-them-to-avo.patch [bz#1038540]
- kvm-migration-fix-free-XBZRLE-decoded_buf-wrong.patch [bz#1038540]
- kvm-block-resize-backing-file-image-during-offline-commi.patch [bz#1047254]
- kvm-block-resize-backing-image-during-active-layer-commi.patch [bz#1047254]
- kvm-block-update-block-commit-documentation-regarding-im.patch [bz#1047254]
- kvm-block-Fix-bdrv_commit-return-value.patch [bz#1047254]
- kvm-block-remove-QED-.bdrv_make_empty-implementation.patch [bz#1047254]
- kvm-block-remove-qcow2-.bdrv_make_empty-implementation.patch [bz#1047254]
- kvm-qemu-progress-Drop-unused-include.patch [bz#997878]
- kvm-qemu-progress-Fix-progress-printing-on-SIGUSR1.patch [bz#997878]
- kvm-Documentation-qemu-img-Mention-SIGUSR1-progress-repo.patch [bz#997878]
- Resolves: bz#1004143
  ("test unit ready failed" on LUN 0 delays boot when a virtio-scsi target does not have any disk on LUN 0)
- Resolves: bz#1004197
  (Cannot hot-plug nic in windows VM when the vmem is larger)
- Resolves: bz#1017096
  (Fail to migrate while the size of migrate-compcache less then 4096)
- Resolves: bz#1026314
  (qemu-kvm hang when use '-sandbox on'+'vnc'+'hda')
- Resolves: bz#1038540
  (qemu-kvm aborted while cancel migration then restart it (with page delta compression))
- Resolves: bz#1039530
  (add support for microsoft os descriptors)
- Resolves: bz#1044182
  (Relax qemu-kvm stack protection to -fstack-protector-strong)
- Resolves: bz#1047254
  (qemu-img failed to commit image)
- Resolves: bz#1047448
  (qemu-kvm core  dump in src host when do migration with "migrate_set_capability xbzrle on and migrate_set_cache_size 10000G")
- Resolves: bz#1048080
  (Qemu-kvm NUMA emulation failed)
- Resolves: bz#997878
  (Kill -SIGUSR1 `pidof qemu-img convert` can not get progress of qemu-img)

* Wed Feb 12 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-46.el7
- kvm-block-fix-backing-file-segfault.patch [bz#748906]
- kvm-block-Move-initialisation-of-BlockLimits-to-bdrv_ref.patch [bz#748906]
- kvm-raw-Fix-BlockLimits-passthrough.patch [bz#748906]
- kvm-block-Inherit-opt_transfer_length.patch [bz#748906]
- kvm-block-Update-BlockLimits-when-they-might-have-change.patch [bz#748906]
- kvm-qemu_memalign-Allow-small-alignments.patch [bz#748906]
- kvm-block-Detect-unaligned-length-in-bdrv_qiov_is_aligne.patch [bz#748906]
- kvm-block-Don-t-use-guest-sector-size-for-qemu_blockalig.patch [bz#748906]
- kvm-block-rename-buffer_alignment-to-guest_block_size.patch [bz#748906]
- kvm-raw-Probe-required-direct-I-O-alignment.patch [bz#748906]
- kvm-block-Introduce-bdrv_aligned_preadv.patch [bz#748906]
- kvm-block-Introduce-bdrv_co_do_preadv.patch [bz#748906]
- kvm-block-Introduce-bdrv_aligned_pwritev.patch [bz#748906]
- kvm-block-write-Handle-COR-dependency-after-I-O-throttli.patch [bz#748906]
- kvm-block-Introduce-bdrv_co_do_pwritev.patch [bz#748906]
- kvm-block-Switch-BdrvTrackedRequest-to-byte-granularity.patch [bz#748906]
- kvm-block-Allow-waiting-for-overlapping-requests-between.patch [bz#748906]
- kvm-block-use-DIV_ROUND_UP-in-bdrv_co_do_readv.patch [bz#748906]
- kvm-block-Make-zero-after-EOF-work-with-larger-alignment.patch [bz#748906]
- kvm-block-Generalise-and-optimise-COR-serialisation.patch [bz#748906]
- kvm-block-Make-overlap-range-for-serialisation-dynamic.patch [bz#748906]
- kvm-block-Fix-32-bit-truncation-in-mark_request_serialis.patch [bz#748906]
- kvm-block-Allow-wait_serialising_requests-at-any-point.patch [bz#748906]
- kvm-block-Align-requests-in-bdrv_co_do_pwritev.patch [bz#748906]
- kvm-lock-Fix-memory-leaks-in-bdrv_co_do_pwritev.patch [bz#748906]
- kvm-block-Assert-serialisation-assumptions-in-pwritev.patch [bz#748906]
- kvm-block-Change-coroutine-wrapper-to-byte-granularity.patch [bz#748906]
- kvm-block-Make-bdrv_pread-a-bdrv_prwv_co-wrapper.patch [bz#748906]
- kvm-block-Make-bdrv_pwrite-a-bdrv_prwv_co-wrapper.patch [bz#748906]
- kvm-iscsi-Set-bs-request_alignment.patch [bz#748906]
- kvm-blkdebug-Make-required-alignment-configurable.patch [bz#748906]
- kvm-blkdebug-Don-t-leak-bs-file-on-failure.patch [bz#748906]
- kvm-qemu-io-New-command-sleep.patch [bz#748906]
- kvm-qemu-iotests-Filter-out-qemu-io-prompt.patch [bz#748906]
- kvm-qemu-iotests-Test-pwritev-RMW-logic.patch [bz#748906]
- kvm-block-bdrv_aligned_pwritev-Assert-overlap-range.patch [bz#748906]
- kvm-block-Don-t-call-ROUND_UP-with-negative-values.patch [bz#748906]
- Resolves: bz#748906
  (qemu fails on disk with 4k sectors and cache=off)

* Wed Feb 05 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-45.el7
- kvm-vfio-pci-Fail-initfn-on-DMA-mapping-errors.patch [bz#1044815]
- kvm-vfio-Destroy-memory-regions.patch [bz#1052030]
- kvm-docs-qcow2-compat-1.1-is-now-the-default.patch [bz#1048092]
- kvm-hda-codec-disable-streams-on-reset.patch [bz#947812]
- kvm-QEMUBH-make-AioContext-s-bh-re-entrant.patch [bz#1009297]
- kvm-qxl-replace-pipe-signaling-with-bottom-half.patch [bz#1009297]
- Resolves: bz#1009297
  (RHEL7.0 guest gui can not be used in dest host after migration)
- Resolves: bz#1044815
  (vfio initfn succeeds even if IOMMU mappings fail)
- Resolves: bz#1048092
  (manpage of qemu-img contains error statement about compat option)
- Resolves: bz#1052030
  (src qemu-kvm core dump after hotplug/unhotplug GPU device and do local migration)
- Resolves: bz#947812
  (There's a shot voice after  'system_reset'  during playing music inside rhel6 guest w/ intel-hda device)

* Wed Jan 29 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-44.el7
- kvm-Partially-revert-rhel-Drop-cfi.pflash01-and-isa-ide-.patch [bz#1032346]
- kvm-Revert-pc-Disable-the-use-flash-device-for-BIOS-unle.patch [bz#1032346]
- kvm-memory-Replace-open-coded-memory_region_is_romd.patch [bz#1032346]
- kvm-memory-Rename-readable-flag-to-romd_mode.patch [bz#1032346]
- kvm-isapc-Fix-non-KVM-qemu-boot-read-write-memory-for-is.patch [bz#1032346]
- kvm-add-kvm_readonly_mem_enabled.patch [bz#1032346]
- kvm-support-using-KVM_MEM_READONLY-flag-for-regions.patch [bz#1032346]
- kvm-pc_sysfw-allow-flash-pflash-memory-to-be-used-with-K.patch [bz#1032346]
- kvm-fix-double-free-the-memslot-in-kvm_set_phys_mem.patch [bz#1032346]
- kvm-sysfw-remove-read-only-pc_sysfw_flash_vs_rom_bug_com.patch [bz#1032346]
- kvm-pc_sysfw-remove-the-rom_only-property.patch [bz#1032346]
- kvm-pc_sysfw-do-not-make-it-a-device-anymore.patch [bz#1032346]
- kvm-hw-i386-pc_sysfw-support-two-flash-drives.patch [bz#1032346]
- kvm-i440fx-test-qtest_start-should-be-paired-with-qtest_.patch [bz#1032346]
- kvm-i440fx-test-give-each-GTest-case-its-own-qtest.patch [bz#1032346]
- kvm-i440fx-test-generate-temporary-firmware-blob.patch [bz#1032346]
- kvm-i440fx-test-verify-firmware-under-4G-and-1M-both-bio.patch [bz#1032346]
- kvm-piix-fix-32bit-pci-hole.patch [bz#1032346]
- kvm-qapi-Add-backing-to-BlockStats.patch [bz#1041564]
- kvm-pc-Disable-RDTSCP-unconditionally-on-rhel6.-machine-.patch [bz#918907]
- kvm-pc-Disable-RDTSCP-on-AMD-CPU-models.patch [bz#1056428 bz#874400]
- kvm-block-add-.bdrv_reopen_prepare-stub-for-iscsi.patch [bz#1030301]
- Resolves: bz#1030301
  (qemu-img can not merge live snapshot to backing file(r/w backing file via libiscsi))
- Resolves: bz#1032346
  (basic OVMF support (non-volatile UEFI variables in flash, and fixup for ACPI tables))
- Resolves: bz#1041564
  ([NFR] qemu: Returning the watermark for all the images opened for writing)
- Resolves: bz#1056428
  ("rdtscp" flag defined on Opteron_G5 model and cann't be exposed to guest)
- Resolves: bz#874400
  ("rdtscp" flag defined on Opteron_G5 model and cann't be exposed to guest)
- Resolves: bz#918907
  (provide backwards-compatible RHEL specific machine types in QEMU - CPU features)

* Mon Jan 27 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-43.el7
- kvm-piix-gigabyte-alignment-for-ram.patch [bz#1026548]
- kvm-pc_piix-document-gigabyte_align.patch [bz#1026548]
- kvm-q35-gigabyle-alignment-for-ram.patch [bz#1026548]
- kvm-virtio-bus-remove-vdev-field.patch [bz#983344]
- kvm-virtio-pci-remove-vdev-field.patch [bz#983344]
- kvm-virtio-bus-cleanup-plug-unplug-interface.patch [bz#983344]
- kvm-virtio-blk-switch-exit-callback-to-VirtioDeviceClass.patch [bz#983344]
- kvm-virtio-serial-switch-exit-callback-to-VirtioDeviceCl.patch [bz#983344]
- kvm-virtio-net-switch-exit-callback-to-VirtioDeviceClass.patch [bz#983344]
- kvm-virtio-scsi-switch-exit-callback-to-VirtioDeviceClas.patch [bz#983344]
- kvm-virtio-balloon-switch-exit-callback-to-VirtioDeviceC.patch [bz#983344]
- kvm-virtio-rng-switch-exit-callback-to-VirtioDeviceClass.patch [bz#983344]
- kvm-virtio-pci-add-device_unplugged-callback.patch [bz#983344]
- kvm-block-use-correct-filename-for-error-report.patch [bz#1051438]
- Resolves: bz#1026548
  (i386: pc: align gpa<->hpa on 1GB boundary)
- Resolves: bz#1051438
  (Error message contains garbled characters when unable to open image due to bad permissions (permission denied).)
- Resolves: bz#983344
  (QEMU core dump and host will reboot when do hot-unplug a virtio-blk disk which use  the switch behind switch)

* Fri Jan 24 2014 Daniel Mach <dmach@redhat.com> - 10:1.5.3-42
- Mass rebuild 2014-01-24

* Wed Jan 22 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-41.el7
- kvm-help-add-id-suboption-to-iscsi.patch [bz#1019221]
- kvm-scsi-disk-add-UNMAP-limits-to-block-limits-VPD-page.patch [bz#1037503]
- kvm-qdev-Fix-32-bit-compilation-in-print_size.patch [bz#1034876]
- kvm-qdev-Use-clz-in-print_size.patch [bz#1034876]
- Resolves: bz#1019221
  (Iscsi miss id sub-option in help output)
- Resolves: bz#1034876
  (export acpi tables to guests)
- Resolves: bz#1037503
  (fix thin provisioning support for block device backends)

* Wed Jan 22 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-40.el7
- kvm-avoid-a-bogus-COMPLETED-CANCELLED-transition.patch [bz#1053699]
- kvm-introduce-MIG_STATE_CANCELLING-state.patch [bz#1053699]
- kvm-vvfat-use-bdrv_new-to-allocate-BlockDriverState.patch [bz#1041301]
- kvm-block-implement-reference-count-for-BlockDriverState.patch [bz#1041301]
- kvm-block-make-bdrv_delete-static.patch [bz#1041301]
- kvm-migration-omit-drive-ref-as-we-have-bdrv_ref-now.patch [bz#1041301]
- kvm-xen_disk-simplify-blk_disconnect-with-refcnt.patch [bz#1041301]
- kvm-nbd-use-BlockDriverState-refcnt.patch [bz#1041301]
- kvm-block-use-BDS-ref-for-block-jobs.patch [bz#1041301]
- kvm-block-Make-BlockJobTypes-const.patch [bz#1041301]
- kvm-blockjob-rename-BlockJobType-to-BlockJobDriver.patch [bz#1041301]
- kvm-qapi-Introduce-enum-BlockJobType.patch [bz#1041301]
- kvm-qapi-make-use-of-new-BlockJobType.patch [bz#1041301]
- kvm-mirror-Don-t-close-target.patch [bz#1041301]
- kvm-mirror-Move-base-to-MirrorBlockJob.patch [bz#1041301]
- kvm-block-Add-commit_active_start.patch [bz#1041301]
- kvm-commit-Support-commit-active-layer.patch [bz#1041301]
- kvm-qemu-iotests-prefill-some-data-to-test-image.patch [bz#1041301]
- kvm-qemu-iotests-Update-test-cases-for-commit-active.patch [bz#1041301]
- kvm-commit-Remove-unused-check.patch [bz#1041301]
- kvm-blockdev-use-bdrv_getlength-in-qmp_drive_mirror.patch [bz#921890]
- kvm-qemu-iotests-make-assert_no_active_block_jobs-common.patch [bz#921890]
- kvm-block-drive-mirror-Check-for-NULL-backing_hd.patch [bz#921890]
- kvm-qemu-iotests-Extend-041-for-unbacked-mirroring.patch [bz#921890]
- kvm-qapi-schema-Update-description-for-NewImageMode.patch [bz#921890]
- kvm-block-drive-mirror-Reuse-backing-HD-for-sync-none.patch [bz#921890]
- kvm-qemu-iotests-Fix-test-041.patch [bz#921890]
- kvm-scsi-bus-fix-transfer-length-and-direction-for-VERIF.patch [bz#1035644]
- kvm-scsi-disk-fix-VERIFY-emulation.patch [bz#1035644]
- kvm-block-ensure-bdrv_drain_all-works-during-bdrv_delete.patch [bz#1041301]
- kvm-use-recommended-max-vcpu-count.patch [bz#998708]
- kvm-pc-Create-pc_compat_rhel-functions.patch [bz#1049706]
- kvm-pc-Enable-x2apic-by-default-on-more-recent-CPU-model.patch [bz#1049706]
- kvm-Build-all-subpackages-for-RHEV.patch [bz#1007204]
- Resolves: bz#1007204
  (qemu-img-rhev  qemu-kvm-rhev-tools are not built for qemu-kvm-1.5.3-3.el7)
- Resolves: bz#1035644
  (rhel7.0host + windows guest + virtio-win + 'chkdsk' in the guest gives qemu assertion in scsi_dma_complete)
- Resolves: bz#1041301
  (live snapshot merge (commit) of the active layer)
- Resolves: bz#1049706
  (MIss CPUID_EXT_X2APIC in Westmere cpu model)
- Resolves: bz#1053699
  (Backport Cancelled race condition fixes)
- Resolves: bz#921890
  (Core dump when block mirror with "sync" is "none" and mode is "absolute-paths")
- Resolves: bz#998708
  (qemu-kvm: maximum vcpu should be recommended maximum)

* Tue Jan 21 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-39.el7
- kvm-Revert-qdev-monitor-Fix-crash-when-device_add-is-cal.patch [bz#669524]
- kvm-Revert-qdev-Do-not-let-the-user-try-to-device_add-wh.patch [bz#669524]
- kvm-qdev-monitor-Clean-up-qdev_device_add-variable-namin.patch [bz#669524]
- kvm-qdev-monitor-Fix-crash-when-device_add-is-called.2.patch.patch [bz#669524]
- kvm-qdev-monitor-Avoid-qdev-as-variable-name.patch [bz#669524]
- kvm-qdev-monitor-Inline-qdev_init-for-device_add.patch [bz#669524]
- kvm-qdev-Do-not-let-the-user-try-to-device_add-when-it.2.patch.patch [bz#669524]
- kvm-qdev-monitor-Avoid-device_add-crashing-on-non-device.patch [bz#669524]
- kvm-qdev-monitor-Improve-error-message-for-device-nonexi.patch [bz#669524]
- kvm-exec-change-well-known-physical-sections-to-macros.patch [bz#1003535]
- kvm-exec-separate-sections-and-nodes-per-address-space.patch [bz#1003535]
- Resolves: bz#1003535
  (qemu-kvm core dump when boot vm with more than 32 virtio disks/nics)
- Resolves: bz#669524
  (Confusing error message from -device <unknown dev>)

* Fri Jan 17 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-38.el7
- kvm-intel-hda-fix-position-buffer.patch [bz#947785]
- kvm-The-calculation-of-bytes_xfer-in-qemu_put_buffer-is-.patch [bz#1003467]
- kvm-migration-Fix-rate-limit.patch [bz#1003467]
- kvm-audio-honor-QEMU_AUDIO_TIMER_PERIOD-instead-of-wakin.patch [bz#1017636]
- kvm-audio-Lower-default-wakeup-rate-to-100-times-second.patch [bz#1017636]
- kvm-audio-adjust-pulse-to-100Hz-wakeup-rate.patch [bz#1017636]
- kvm-pc-Fix-rhel6.-3dnow-3dnowext-compat-bits.patch [bz#918907]
- kvm-add-firmware-to-machine-options.patch [bz#1038603]
- kvm-switch-rhel7-machine-types-to-big-bios.patch [bz#1038603]
- kvm-add-bios-256k.bin-from-seabios-bin-1.7.2.2-10.el7.no.patch [bz#1038603]
- kvm-pci-fix-pci-bridge-fw-path.patch [bz#1034518]
- kvm-hw-cannot_instantiate_with_device_add_yet-due-to-poi.patch [bz#1031098]
- kvm-qdev-Document-that-pointer-properties-kill-device_ad.patch [bz#1031098]
- kvm-Add-back-no-hpet-but-ignore-it.patch [bz#1044742]
- Resolves: bz#1003467
  (Backport migration fixes from post qemu 1.6)
- Resolves: bz#1017636
  (PATCH: fix qemu using 50% host cpu when audio is playing)
- Resolves: bz#1031098
  (Disable device smbus-eeprom)
- Resolves: bz#1034518
  (boot order wrong with q35)
- Resolves: bz#1038603
  (make seabios 256k for rhel7 machine types)
- Resolves: bz#1044742
  (Cannot create guest on remote RHEL7 host using F20 virt-manager, libvirt's qemu -no-hpet detection is broken)
- Resolves: bz#918907
  (provide backwards-compatible RHEL specific machine types in QEMU - CPU features)
- Resolves: bz#947785
  (In rhel6.4 guest  sound recorder doesn't work when  playing audio)

* Wed Jan 15 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-37.el7
- kvm-bitmap-use-long-as-index.patch [bz#997559]
- kvm-memory-cpu_physical_memory_set_dirty_flags-result-is.patch [bz#997559]
- kvm-memory-cpu_physical_memory_set_dirty_range-return-vo.patch [bz#997559]
- kvm-exec-use-accessor-function-to-know-if-memory-is-dirt.patch [bz#997559]
- kvm-memory-create-function-to-set-a-single-dirty-bit.patch [bz#997559]
- kvm-exec-drop-useless-if.patch [bz#997559]
- kvm-exec-create-function-to-get-a-single-dirty-bit.patch [bz#997559]
- kvm-memory-make-cpu_physical_memory_is_dirty-return-bool.patch [bz#997559]
- kvm-memory-all-users-of-cpu_physical_memory_get_dirty-us.patch [bz#997559]
- kvm-memory-set-single-dirty-flags-when-possible.patch [bz#997559]
- kvm-memory-cpu_physical_memory_set_dirty_range-always-di.patch [bz#997559]
- kvm-memory-cpu_physical_memory_mask_dirty_range-always-c.patch [bz#997559]
- kvm-memory-use-bit-2-for-migration.patch [bz#997559]
- kvm-memory-make-sure-that-client-is-always-inside-range.patch [bz#997559]
- kvm-memory-only-resize-dirty-bitmap-when-memory-size-inc.patch [bz#997559]
- kvm-memory-cpu_physical_memory_clear_dirty_flag-result-i.patch [bz#997559]
- kvm-bitmap-Add-bitmap_zero_extend-operation.patch [bz#997559]
- kvm-memory-split-dirty-bitmap-into-three.patch [bz#997559]
- kvm-memory-unfold-cpu_physical_memory_clear_dirty_flag-i.patch [bz#997559]
- kvm-memory-unfold-cpu_physical_memory_set_dirty-in-its-o.patch [bz#997559]
- kvm-memory-unfold-cpu_physical_memory_set_dirty_flag.patch [bz#997559]
- kvm-memory-make-cpu_physical_memory_get_dirty-the-main-f.patch [bz#997559]
- kvm-memory-cpu_physical_memory_get_dirty-is-used-as-retu.patch [bz#997559]
- kvm-memory-s-mask-clear-cpu_physical_memory_mask_dirty_r.patch [bz#997559]
- kvm-memory-use-find_next_bit-to-find-dirty-bits.patch [bz#997559]
- kvm-memory-cpu_physical_memory_set_dirty_range-now-uses-.patch [bz#997559]
- kvm-memory-cpu_physical_memory_clear_dirty_range-now-use.patch [bz#997559]
- kvm-memory-s-dirty-clean-in-cpu_physical_memory_is_dirty.patch [bz#997559]
- kvm-memory-make-cpu_physical_memory_reset_dirty-take-a-l.patch [bz#997559]
- kvm-exec-Remove-unused-global-variable-phys_ram_fd.patch [bz#997559]
- kvm-memory-cpu_physical_memory_set_dirty_tracking-should.patch [bz#997559]
- kvm-memory-move-private-types-to-exec.c.patch [bz#997559]
- kvm-memory-split-cpu_physical_memory_-functions-to-its-o.patch [bz#997559]
- kvm-memory-unfold-memory_region_test_and_clear.patch [bz#997559]
- kvm-use-directly-cpu_physical_memory_-api-for-tracki.patch [bz#997559]
- kvm-refactor-start-address-calculation.patch [bz#997559]
- kvm-memory-move-bitmap-synchronization-to-its-own-functi.patch [bz#997559]
- kvm-memory-syncronize-kvm-bitmap-using-bitmaps-operation.patch [bz#997559]
- kvm-ram-split-function-that-synchronizes-a-range.patch [bz#997559]
- kvm-migration-synchronize-memory-bitmap-64bits-at-a-time.patch [bz#997559]
- Resolves: bz#997559
  (Improve live migration bitmap handling)

* Tue Jan 14 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-36.el7
- kvm-Add-support-statement-to-help-output.patch [bz#972773]
- kvm-__com.redhat_qxl_screendump-add-docs.patch [bz#903910]
- kvm-vl-Round-memory-sizes-below-2MiB-up-to-2MiB.patch [bz#999836]
- kvm-seccomp-exit-if-seccomp_init-fails.patch [bz#1044845]
- kvm-redhat-qemu-kvm.spec-require-python-for-build.patch [bz#1034876]
- kvm-redhat-qemu-kvm.spec-require-iasl.patch [bz#1034876]
- kvm-configure-make-iasl-option-actually-work.patch [bz#1034876]
- kvm-redhat-qemu-kvm.spec-add-cpp-as-build-dependency.patch [bz#1034876]
- kvm-acpi-build-disable-with-no-acpi.patch [bz#1045386]
- kvm-ehci-implement-port-wakeup.patch [bz#1039513]
- kvm-qdev-monitor-Fix-crash-when-device_add-is-called-wit.patch [bz#1026712 bz#1046007]
- kvm-block-vhdx-improve-error-message-and-.bdrv_check-imp.patch [bz#1035001]
- kvm-docs-updated-qemu-img-man-page-and-qemu-doc-to-refle.patch [bz#1017650]
- kvm-enable-pvticketlocks-by-default.patch [bz#1052340]
- kvm-fix-boot-strict-regressed-in-commit-6ef4716.patch [bz#997817]
- kvm-vl-make-boot_strict-variable-static-not-used-outside.patch [bz#997817]
- Resolves: bz#1017650
  (need to update qemu-img man pages on "VHDX" format)
- Resolves: bz#1026712
  (Qemu core dumpd when boot guest with driver name as "virtio-pci")
- Resolves: bz#1034876
  (export acpi tables to guests)
- Resolves: bz#1035001
  (VHDX: journal log should not be replayed by default, but rather via qemu-img check -r all)
- Resolves: bz#1039513
  (backport remote wakeup for ehci)
- Resolves: bz#1044845
  (QEMU seccomp sandbox - exit if seccomp_init() fails)
- Resolves: bz#1045386
  (qemu-kvm: hw/i386/acpi-build.c:135: acpi_get_pm_info: Assertion `obj' failed.)
- Resolves: bz#1046007
  (qemu-kvm aborted when hot plug PCI device to guest with romfile and rombar=0)
- Resolves: bz#1052340
  (pvticketlocks: default on)
- Resolves: bz#903910
  (RHEL7 does not have equivalent functionality for __com.redhat_qxl_screendump)
- Resolves: bz#972773
  (RHEL7: Clarify support statement in KVM help)
- Resolves: bz#997817
  (-boot order and -boot once regressed since RHEL-6)
- Resolves: bz#999836
  (-m 1 crashes)

* Thu Jan 09 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-35.el7
- kvm-option-Add-assigned-flag-to-QEMUOptionParameter.patch [bz#1033490]
- kvm-qcow2-refcount-Snapshot-update-for-zero-clusters.patch [bz#1033490]
- kvm-qemu-iotests-Snapshotting-zero-clusters.patch [bz#1033490]
- kvm-block-Image-file-option-amendment.patch [bz#1033490]
- kvm-qcow2-cache-Empty-cache.patch [bz#1033490]
- kvm-qcow2-cluster-Expand-zero-clusters.patch [bz#1033490]
- kvm-qcow2-Save-refcount-order-in-BDRVQcowState.patch [bz#1033490]
- kvm-qcow2-Implement-bdrv_amend_options.patch [bz#1033490]
- kvm-qcow2-Correct-bitmap-size-in-zero-expansion.patch [bz#1033490]
- kvm-qcow2-Free-only-newly-allocated-clusters-on-error.patch [bz#1033490]
- kvm-qcow2-Add-missing-space-in-error-message.patch [bz#1033490]
- kvm-qemu-iotest-qcow2-image-option-amendment.patch [bz#1033490]
- kvm-qemu-iotests-New-test-case-in-061.patch [bz#1033490]
- kvm-qemu-iotests-Preallocated-zero-clusters-in-061.patch [bz#1033490]
- Resolves: bz#1033490
  (Cannot upgrade/downgrade qcow2 images)

* Wed Jan 08 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-34.el7
- kvm-block-stream-Don-t-stream-unbacked-devices.patch [bz#965636]
- kvm-qemu-io-Let-open-pass-options-to-block-driver.patch [bz#1004347]
- kvm-qcow2.py-Subcommand-for-changing-header-fields.patch [bz#1004347]
- kvm-qemu-iotests-Remaining-error-propagation-adjustments.patch [bz#1004347]
- kvm-qemu-iotests-Add-test-for-inactive-L2-overlap.patch [bz#1004347]
- kvm-qemu-iotests-Adjust-test-result-039.patch [bz#1004347]
- kvm-virtio-net-don-t-update-mac_table-in-error-state.patch [bz#1048671]
- kvm-qcow2-Zero-initialise-first-cluster-for-new-images.patch [bz#1032904]
- Resolves: bz#1004347
  (Backport qcow2 corruption prevention patches)
- Resolves: bz#1032904
  (qemu-img can not create libiscsi qcow2_v3 image)
- Resolves: bz#1048671
  (virtio-net: mac_table change isn't recovered in error state)
- Resolves: bz#965636
  (streaming with no backing file should not do anything)

* Wed Jan 08 2014 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-33.el7
- kvm-block-qemu-iotests-for-vhdx-read-sample-dynamic-imag.patch [bz#879234]
- kvm-block-qemu-iotests-add-quotes-to-TEST_IMG-usage-io-p.patch [bz#879234]
- kvm-block-qemu-iotests-fix-_make_test_img-to-work-with-s.patch [bz#879234]
- kvm-block-qemu-iotests-add-quotes-to-TEST_IMG.base-usage.patch [bz#879234]
- kvm-block-qemu-iotests-add-quotes-to-TEST_IMG-usage-in-0.patch [bz#879234]
- kvm-block-qemu-iotests-removes-duplicate-double-quotes-i.patch [bz#879234]
- kvm-block-vhdx-minor-comments-and-typo-correction.patch [bz#879234]
- kvm-block-vhdx-add-header-update-capability.patch [bz#879234]
- kvm-block-vhdx-code-movement-VHDXMetadataEntries-and-BDR.patch [bz#879234]
- kvm-block-vhdx-log-support-struct-and-defines.patch [bz#879234]
- kvm-block-vhdx-break-endian-translation-functions-out.patch [bz#879234]
- kvm-block-vhdx-update-log-guid-in-header-and-first-write.patch [bz#879234]
- kvm-block-vhdx-code-movement-move-vhdx_close-above-vhdx_.patch [bz#879234]
- kvm-block-vhdx-log-parsing-replay-and-flush-support.patch [bz#879234]
- kvm-block-vhdx-add-region-overlap-detection-for-image-fi.patch [bz#879234]
- kvm-block-vhdx-add-log-write-support.patch [bz#879234]
- kvm-block-vhdx-write-support.patch [bz#879234]
- kvm-block-vhdx-remove-BAT-file-offset-bit-shifting.patch [bz#879234]
- kvm-block-vhdx-move-more-endian-translations-to-vhdx-end.patch [bz#879234]
- kvm-block-vhdx-break-out-code-operations-to-functions.patch [bz#879234]
- kvm-block-vhdx-fix-comment-typos-in-header-fix-incorrect.patch [bz#879234]
- kvm-block-vhdx-add-.bdrv_create-support.patch [bz#879234]
- kvm-block-vhdx-update-_make_test_img-to-filter-out-vhdx-.patch [bz#879234]
- kvm-block-qemu-iotests-for-vhdx-add-write-test-support.patch [bz#879234]
- kvm-block-vhdx-qemu-iotest-log-replay-of-data-sector.patch [bz#879234]
- Resolves: bz#879234
  ([RFE] qemu-img: Add/improve support for VHDX format)

* Mon Jan 06 2014 Michal Novotny <minovotn@redhat.com> - 1.5.3-32.el7
- kvm-block-change-default-of-.has_zero_init-to-0.patch.patch [bz#1007815]
- kvm-iscsi-factor-out-sector-conversions.patch.patch [bz#1007815]
- kvm-iscsi-add-logical-block-provisioning-information-to-.patch.patch [bz#1007815]
- kvm-iscsi-add-.bdrv_get_block_status.patch.patch.patch [bz#1007815]
- kvm-iscsi-split-discard-requests-in-multiple-parts.patch.patch.patch [bz#1007815]
- kvm-block-make-BdrvRequestFlags-public.patch.patch.patch [bz#1007815]
- kvm-block-add-flags-to-bdrv_-_write_zeroes.patch.patch.patch [bz#1007815]
- kvm-block-introduce-BDRV_REQ_MAY_UNMAP-request-flag.patch.patch.patch [bz#1007815]
- kvm-block-add-logical-block-provisioning-info-to-BlockDr.patch.patch.patch [bz#1007815]
- kvm-block-add-wrappers-for-logical-block-provisioning-in.patch.patch.patch [bz#1007815]
- kvm-block-iscsi-add-.bdrv_get_info.patch.patch [bz#1007815]
- kvm-block-add-BlockLimits-structure-to-BlockDriverState.patch.patch.patch [bz#1007815]
- kvm-block-raw-copy-BlockLimits-on-raw_open.patch.patch.patch [bz#1007815]
- kvm-block-honour-BlockLimits-in-bdrv_co_do_write_zeroes.patch.patch.patch [bz#1007815]
- kvm-block-honour-BlockLimits-in-bdrv_co_discard.patch.patch.patch [bz#1007815]
- kvm-iscsi-set-limits-in-BlockDriverState.patch.patch.patch [bz#1007815]
- kvm-iscsi-simplify-iscsi_co_discard.patch.patch.patch [bz#1007815]
- kvm-iscsi-add-bdrv_co_write_zeroes.patch.patch.patch [bz#1007815]
- kvm-block-introduce-bdrv_make_zero.patch.patch.patch [bz#1007815]
- kvm-block-get_block_status-fix-BDRV_BLOCK_ZERO-for-unall.patch.patch.patch [bz#1007815]
- kvm-qemu-img-add-support-for-fully-allocated-images.patch.patch.patch [bz#1007815]
- kvm-qemu-img-conditionally-zero-out-target-on-convert.patch.patch.patch [bz#1007815]
- kvm-block-generalize-BlockLimits-handling-to-cover-bdrv_.patch.patch.patch [bz#1007815]
- kvm-block-add-flags-to-BlockRequest.patch.patch.patch [bz#1007815]
- kvm-block-add-flags-argument-to-bdrv_co_write_zeroes-tra.patch.patch.patch [bz#1007815]
- kvm-block-add-bdrv_aio_write_zeroes.patch.patch.patch [bz#1007815]
- kvm-block-handle-ENOTSUP-from-discard-in-generic-code.patch.patch.patch [bz#1007815]
- kvm-block-make-bdrv_co_do_write_zeroes-stricter-in-produ.patch.patch.patch [bz#1007815]
- kvm-vpc-vhdx-add-get_info.patch.patch.patch [bz#1007815]
- kvm-block-drivers-add-discard-write_zeroes-properties-to.patch.patch.patch [bz#1007815]
- kvm-block-drivers-expose-requirement-for-write-same-alig.patch.patch.patch [bz#1007815]
- kvm-block-iscsi-remove-.bdrv_has_zero_init.patch.patch.patch [bz#1007815]
- kvm-block-iscsi-updated-copyright.patch.patch.patch [bz#1007815]
- kvm-block-iscsi-check-WRITE-SAME-support-differently-dep.patch.patch.patch [bz#1007815]
- kvm-scsi-disk-catch-write-protection-errors-in-UNMAP.patch.patch.patch [bz#1007815]
- kvm-scsi-disk-reject-ANCHOR-1-for-UNMAP-and-WRITE-SAME-c.patch.patch.patch [bz#1007815]
- kvm-scsi-disk-correctly-implement-WRITE-SAME.patch.patch.patch [bz#1007815]
- kvm-scsi-disk-fix-WRITE-SAME-with-large-non-zero-payload.patch.patch.patch [bz#1007815]
- kvm-raw-posix-implement-write_zeroes-with-MAY_UNMAP-for-.patch.patch.patch.patch [bz#1007815]
- kvm-raw-posix-implement-write_zeroes-with-MAY_UNMAP-for-.patch.patch.patch.patch.patch [bz#1007815]
- kvm-raw-posix-add-support-for-write_zeroes-on-XFS-and-bl.patch.patch [bz#1007815]
- kvm-qemu-iotests-033-is-fast.patch.patch [bz#1007815]
- kvm-qemu-img-add-support-for-skipping-zeroes-in-input-du.patch.patch [bz#1007815]
- kvm-qemu-img-fix-usage-instruction-for-qemu-img-convert.patch.patch [bz#1007815]
- kvm-block-iscsi-set-bdi-cluster_size.patch.patch [bz#1007815]
- kvm-block-add-opt_transfer_length-to-BlockLimits.patch.patch [bz#1039557]
- kvm-block-iscsi-set-bs-bl.opt_transfer_length.patch.patch [bz#1039557]
- kvm-qemu-img-dynamically-adjust-iobuffer-size-during-con.patch.patch [bz#1039557]
- kvm-qemu-img-round-down-request-length-to-an-aligned-sec.patch.patch [bz#1039557]
- kvm-qemu-img-decrease-progress-update-interval-on-conver.patch.patch [bz#1039557]
- Resolves: bz#1007815
  (fix WRITE SAME support)
- Resolves: bz#1039557
  (optimize qemu-img for thin provisioned images)

* Fri Dec 27 2013 Daniel Mach <dmach@redhat.com> - 10:1.5.3-31
- Mass rebuild 2013-12-27

* Wed Dec 18 2013 Michal Novotny <minovotn@redhat.com> - 1.5.3-30.el7
- kvm-Revert-HMP-Disable-drive_add-for-Red-Hat-Enterprise-2.patch.patch [bz#889051]
- Resolves: bz#889051
  (Commands "__com.redhat_drive_add/del" don' t exist in RHEL7.0)

* Wed Dec 18 2013 Michal Novotny <minovotn@redhat.com> - 1.5.3-29.el7
- kvm-QMP-Forward-port-__com.redhat_drive_del-from-RHEL-6.patch [bz#889051]
- kvm-QMP-Forward-port-__com.redhat_drive_add-from-RHEL-6.patch [bz#889051]
- kvm-HMP-Forward-port-__com.redhat_drive_add-from-RHEL-6.patch [bz#889051]
- kvm-QMP-Document-throttling-parameters-of-__com.redhat_d.patch [bz#889051]
- kvm-HMP-Disable-drive_add-for-Red-Hat-Enterprise-Linux.patch [bz#889051]
- Resolves: bz#889051
  (Commands "__com.redhat_drive_add/del" don' t exist in RHEL7.0)

* Wed Dec 18 2013 Michal Novotny <minovotn@redhat.com> - 1.5.3-28.el7
- kvm-virtio_pci-fix-level-interrupts-with-irqfd.patch [bz#1035132]
- Resolves: bz#1035132
  (fail to boot and call trace with x-data-plane=on specified for rhel6.5 guest)

* Wed Dec 18 2013 Michal Novotny <minovotn@redhat.com> - 1.5.3-27.el7
- Change systemd service location [bz#1025217]
- kvm-vmdk-Allow-read-only-open-of-VMDK-version-3.patch [bz#1007710 bz#1029852]
- Resolves: bz#1007710
  ([RFE] Enable qemu-img to support VMDK version 3)
- Resolves: bz#1025217
  (systemd can't control ksm.service and ksmtuned.service)
- Resolves: bz#1029852
  (qemu-img fails to convert vmdk image with "qemu-img: Could not open 'image.vmdk'")

* Wed Dec 18 2013 Michal Novotny <minovotn@redhat.com> - 1.5.3-26.el7
- Add BuildRequires to libRDMAcm-devel for RDMA support [bz#1011720]
- kvm-add-a-header-file-for-atomic-operations.patch [bz#1011720]
- kvm-savevm-Fix-potential-memory-leak.patch [bz#1011720]
- kvm-migration-Fail-migration-on-bdrv_flush_all-error.patch [bz#1011720]
- kvm-rdma-add-documentation.patch [bz#1011720]
- kvm-rdma-introduce-qemu_update_position.patch [bz#1011720]
- kvm-rdma-export-yield_until_fd_readable.patch [bz#1011720]
- kvm-rdma-export-throughput-w-MigrationStats-QMP.patch [bz#1011720]
- kvm-rdma-introduce-qemu_file_mode_is_not_valid.patch [bz#1011720]
- kvm-rdma-introduce-qemu_ram_foreach_block.patch [bz#1011720]
- kvm-rdma-new-QEMUFileOps-hooks.patch [bz#1011720]
- kvm-rdma-introduce-capability-x-rdma-pin-all.patch [bz#1011720]
- kvm-rdma-update-documentation-to-reflect-new-unpin-suppo.patch [bz#1011720]- kvm-rdma-bugfix-ram_control_save_page.patch [bz#1011720]
- kvm-rdma-introduce-ram_handle_compressed.patch [bz#1011720]
- kvm-rdma-core-logic.patch [bz#1011720]
- kvm-rdma-send-pc.ram.patch [bz#1011720]
- kvm-rdma-allow-state-transitions-between-other-states-be.patch [bz#1011720]
- kvm-rdma-introduce-MIG_STATE_NONE-and-change-MIG_STATE_S.patch [bz#1011720]
- kvm-rdma-account-for-the-time-spent-in-MIG_STATE_SETUP-t.patch [bz#1011720]
- kvm-rdma-bugfix-make-IPv6-support-work.patch [bz#1011720]
- kvm-rdma-forgot-to-turn-off-the-debugging-flag.patch [bz#1011720]
- kvm-rdma-correct-newlines-in-error-statements.patch [bz#1011720]
- kvm-rdma-don-t-use-negative-index-to-array.patch [bz#1011720]
- kvm-rdma-qemu_rdma_post_send_control-uses-wrongly-RDMA_W.patch [bz#1011720]
- kvm-rdma-use-DRMA_WRID_READY.patch [bz#1011720]
- kvm-rdma-memory-leak-RDMAContext-host.patch [bz#1011720]
- kvm-rdma-use-resp.len-after-validation-in-qemu_rdma_regi.patch [bz#1011720]
- kvm-rdma-validate-RDMAControlHeader-len.patch [bz#1011720]
- kvm-rdma-check-if-RDMAControlHeader-len-match-transferre.patch [bz#1011720]
- kvm-rdma-proper-getaddrinfo-handling.patch [bz#1011720]
- kvm-rdma-IPv6-over-Ethernet-RoCE-is-broken-in-linux-work.patch [bz#1011720]
- kvm-rdma-remaining-documentation-fixes.patch [bz#1011720]
- kvm-rdma-silly-ipv6-bugfix.patch [bz#1011720]
- kvm-savevm-fix-wrong-initialization-by-ram_control_load_.patch [bz#1011720]
- kvm-arch_init-right-return-for-ram_save_iterate.patch [bz#1011720]
- kvm-rdma-clean-up-of-qemu_rdma_cleanup.patch [bz#1011720]
- kvm-rdma-constify-ram_chunk_-index-start-end.patch [bz#1011720]
- kvm-migration-Fix-debug-print-type.patch [bz#1011720]
- kvm-arch_init-make-is_zero_page-accept-size.patch [bz#1011720]
- kvm-migration-ram_handle_compressed.patch [bz#1011720]
- kvm-migration-fix-spice-migration.patch [bz#1011720]
- kvm-pci-assign-cap-number-of-devices-that-can-be-assigne.patch [bz#678368]
- kvm-vfio-cap-number-of-devices-that-can-be-assigned.patch [bz#678368]
- kvm-Revert-usb-tablet-Don-t-claim-wakeup-capability-for-.patch [bz#1039513]
- kvm-mempath-prefault-pages-manually-v4.patch [bz#1026554]
- Resolves: bz#1011720
  ([HP 7.0 Feat]: Backport RDMA based live guest migration changes from upstream to RHEL7.0 KVM)
- Resolves: bz#1026554
  (qemu: mempath: prefault pages manually)
- Resolves: bz#1039513
  (backport remote wakeup for ehci)
- Resolves: bz#678368
  (RFE: Support more than 8 assigned devices)

* Wed Dec 18 2013 Michal Novotny <minovotn@redhat.com> - 1.5.3-25.el7
- kvm-Change-package-description.patch [bz#1017696]
- kvm-seccomp-add-kill-to-the-syscall-whitelist.patch [bz#1026314]
- kvm-json-parser-fix-handling-of-large-whole-number-value.patch [bz#997915]
- kvm-qapi-add-QMP-input-test-for-large-integers.patch [bz#997915]
- kvm-qapi-fix-visitor-serialization-tests-for-numbers-dou.patch [bz#997915]
- kvm-qapi-add-native-list-coverage-for-visitor-serializat.patch [bz#997915]
- kvm-qapi-add-native-list-coverage-for-QMP-output-visitor.patch [bz#997915]
- kvm-qapi-add-native-list-coverage-for-QMP-input-visitor-.patch [bz#997915]
- kvm-qapi-lack-of-two-commas-in-dict.patch [bz#997915]
- kvm-tests-QAPI-schema-parser-tests.patch [bz#997915]
- kvm-tests-Use-qapi-schema-test.json-as-schema-parser-tes.patch [bz#997915]
- kvm-qapi.py-Restructure-lexer-and-parser.patch [bz#997915]
- kvm-qapi.py-Decent-syntax-error-reporting.patch [bz#997915]
- kvm-qapi.py-Reject-invalid-characters-in-schema-file.patch [bz#997915]
- kvm-qapi.py-Fix-schema-parser-to-check-syntax-systematic.patch [bz#997915]
- kvm-qapi.py-Fix-diagnosing-non-objects-at-a-schema-s-top.patch [bz#997915]
- kvm-qapi.py-Rename-expr_eval-to-expr-in-parse_schema.patch [bz#997915]
- kvm-qapi.py-Permit-comments-starting-anywhere-on-the-lin.patch [bz#997915]
- kvm-scripts-qapi.py-Avoid-syntax-not-supported-by-Python.patch [bz#997915]
- kvm-tests-Fix-schema-parser-test-for-in-tree-build.patch [bz#997915]
- Resolves: bz#1017696
  ([branding] remove references to dynamic translation and user-mode emulation)
- Resolves: bz#1026314
  (qemu-kvm hang when use '-sandbox on'+'vnc'+'hda')
- Resolves: bz#997915
  (Backport new QAPI parser proactively to help developers and avoid silly conflicts)

* Tue Dec 17 2013 Michal Novotny <minovotn@redhat.com> - 1.5.3-24.el7
- kvm-range-add-Range-structure.patch [bz#1034876]
- kvm-range-add-Range-to-typedefs.patch [bz#1034876]
- kvm-range-add-min-max-operations-on-ranges.patch [bz#1034876]
- kvm-qdev-Add-SIZE-type-to-qdev-properties.patch [bz#1034876]
- kvm-qapi-make-visit_type_size-fallback-to-type_int.patch [bz#1034876]
- kvm-pc-move-IO_APIC_DEFAULT_ADDRESS-to-include-hw-i386-i.patch [bz#1034876]
- kvm-pci-add-helper-to-retrieve-the-64-bit-range.patch [bz#1034876]
- kvm-pci-fix-up-w64-size-calculation-helper.patch [bz#1034876]
- kvm-refer-to-FWCfgState-explicitly.patch [bz#1034876]
- kvm-fw_cfg-move-typedef-to-qemu-typedefs.h.patch [bz#1034876]
- kvm-arch_init-align-MR-size-to-target-page-size.patch [bz#1034876]
- kvm-loader-store-FW-CFG-ROM-files-in-RAM.patch [bz#1034876]
- kvm-pci-store-PCI-hole-ranges-in-guestinfo-structure.patch [bz#1034876]
- kvm-pc-pass-PCI-hole-ranges-to-Guests.patch [bz#1034876]
- kvm-pc-replace-i440fx_common_init-with-i440fx_init.patch [bz#1034876]
- kvm-pc-don-t-access-fw-cfg-if-NULL.patch [bz#1034876]
- kvm-pc-add-I440FX-QOM-cast-macro.patch [bz#1034876]
- kvm-pc-limit-64-bit-hole-to-2G-by-default.patch [bz#1034876]
- kvm-q35-make-pci-window-address-size-match-guest-cfg.patch [bz#1034876]
- kvm-q35-use-64-bit-window-programmed-by-guest.patch [bz#1034876]
- kvm-piix-use-64-bit-window-programmed-by-guest.patch [bz#1034876]
- kvm-pc-fix-regression-for-64-bit-PCI-memory.patch [bz#1034876]
- kvm-cleanup-object.h-include-error.h-directly.patch [bz#1034876]
- kvm-qom-cleanup-struct-Error-references.patch [bz#1034876]
- kvm-qom-add-pointer-to-int-property-helpers.patch [bz#1034876]
- kvm-fw_cfg-interface-to-trigger-callback-on-read.patch [bz#1034876]
- kvm-loader-support-for-unmapped-ROM-blobs.patch [bz#1034876]
- kvm-pcie_host-expose-UNMAPPED-macro.patch [bz#1034876]
- kvm-pcie_host-expose-address-format.patch [bz#1034876]
- kvm-q35-use-macro-for-MCFG-property-name.patch [bz#1034876]
- kvm-q35-expose-mmcfg-size-as-a-property.patch [bz#1034876]
- kvm-i386-add-ACPI-table-files-from-seabios.patch [bz#1034876]
- kvm-acpi-add-rules-to-compile-ASL-source.patch [bz#1034876]
- kvm-acpi-pre-compiled-ASL-files.patch [bz#1034876]
- kvm-acpi-ssdt-pcihp-updat-generated-file.patch [bz#1034876]
- kvm-loader-use-file-path-size-from-fw_cfg.h.patch [bz#1034876]
- kvm-i386-add-bios-linker-loader.patch [bz#1034876]
- kvm-loader-allow-adding-ROMs-in-done-callbacks.patch [bz#1034876]
- kvm-i386-define-pc-guest-info.patch [bz#1034876]
- kvm-acpi-piix-add-macros-for-acpi-property-names.patch [bz#1034876]
- kvm-piix-APIs-for-pc-guest-info.patch [bz#1034876]
- kvm-ich9-APIs-for-pc-guest-info.patch [bz#1034876]
- kvm-pvpanic-add-API-to-access-io-port.patch [bz#1034876]
- kvm-hpet-add-API-to-find-it.patch [bz#1034876]
- kvm-hpet-fix-build-with-CONFIG_HPET-off.patch [bz#1034876]
- kvm-acpi-add-interface-to-access-user-installed-tables.patch [bz#1034876]
- kvm-pc-use-new-api-to-add-builtin-tables.patch [bz#1034876]
- kvm-i386-ACPI-table-generation-code-from-seabios.patch [bz#1034876]
- kvm-ssdt-fix-PBLK-length.patch [bz#1034876]
- kvm-ssdt-proc-update-generated-file.patch [bz#1034876]
- kvm-pc-disable-pci-info.patch [bz#1034876]
- kvm-acpi-build-fix-build-on-glib-2.22.patch [bz#1034876]
- kvm-acpi-build-fix-build-on-glib-2.14.patch [bz#1034876]
- kvm-acpi-build-fix-support-for-glib-2.22.patch [bz#1034876]
- kvm-acpi-build-Fix-compiler-warning-missing-gnu_printf-f.patch [bz#1034876]
- kvm-exec-Fix-prototype-of-phys_mem_set_alloc-and-related.patch [bz#1034876]
- Resolves: bz#1034876
  (export acpi tables to guests)

* Tue Dec 17 2013 Michal Novotny <minovotn@redhat.com> - 1.5.3-23.el7
- kvm-qdev-monitor-Unref-device-when-device_add-fails.patch [bz#1003773]
- kvm-qdev-Drop-misleading-qdev_free-function.patch [bz#1003773]
- kvm-blockdev-fix-drive_init-opts-and-bs_opts-leaks.patch [bz#1003773]
- kvm-libqtest-rename-qmp-to-qmp_discard_response.patch [bz#1003773]
- kvm-libqtest-add-qmp-fmt-.-QDict-function.patch [bz#1003773]
- kvm-blockdev-test-add-test-case-for-drive_add-duplicate-.patch [bz#1003773]
- kvm-qdev-monitor-test-add-device_add-leak-test-cases.patch [bz#1003773]
- kvm-qtest-Use-display-none-by-default.patch [bz#1003773]
- Resolves: bz#1003773
  (When virtio-blk-pci device with dataplane is failed to be added, the drive cannot be released.)

* Tue Dec 17 2013 Michal Novotny <minovotn@redhat.com> - 1.5.3-22.el7
- Fix ksmtuned with set_process_name=1 [bz#1027420]
- Fix committed memory when no qemu-kvm running [bz#1027418]
- kvm-virtio-net-fix-the-memory-leak-in-rxfilter_notify.patch [bz#1033810]
- kvm-qom-Fix-memory-leak-in-object_property_set_link.patch [bz#1033810]
- kvm-fix-intel-hda-live-migration.patch [bz#1036537]
- kvm-vfio-pci-Release-all-MSI-X-vectors-when-disabled.patch [bz#1029743]
- kvm-Query-KVM-for-available-memory-slots.patch [bz#921490]
- kvm-block-Dont-ignore-previously-set-bdrv_flags.patch [bz#1039501]
- kvm-cleanup-trace-events.pl-New.patch [bz#997832]
- kvm-slavio_misc-Fix-slavio_led_mem_readw-_writew-tracepo.patch [bz#997832]
- kvm-milkymist-minimac2-Fix-minimac2_read-_write-tracepoi.patch [bz#997832]
- kvm-trace-events-Drop-unused-events.patch [bz#997832]
- kvm-trace-events-Fix-up-source-file-comments.patch [bz#997832]
- kvm-trace-events-Clean-up-with-scripts-cleanup-trace-eve.patch [bz#997832]
- kvm-trace-events-Clean-up-after-removal-of-old-usb-host-.patch [bz#997832]
- kvm-net-Update-netdev-peer-on-link-change.patch [bz#1027571]
- Resolves: bz#1027418
  (ksmtuned committed_memory() still returns "", not 0, when no qemu running)
- Resolves: bz#1027420
  (ksmtuned can’t handle libvirt WITH set_process_name=1)
- Resolves: bz#1027571
  ([virtio-win]win8.1 guest network can not resume automatically after do "set_link tap1 on")
- Resolves: bz#1029743
  (qemu-kvm core dump after hot plug/unplug 82576 PF about 100 times)
- Resolves: bz#1033810
  (memory leak in using object_get_canonical_path())
- Resolves: bz#1036537
  (Cross version migration from RHEL6.5 host to RHEL7.0 host with sound device failed.)
- Resolves: bz#1039501
  ([provisioning] discard=on broken)
- Resolves: bz#921490
  (qemu-kvm core dumped after hot plugging more than 11 VF through vfio-pci)
- Resolves: bz#997832
  (Backport trace fixes proactively to avoid confusion and silly conflicts)

* Tue Dec 03 2013 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-21.el7
- kvm-scsi-Allocate-SCSITargetReq-r-buf-dynamically-CVE-20.patch [bz#1007334]
- Resolves: bz#1007334
  (CVE-2013-4344 qemu-kvm: qemu: buffer overflow in scsi_target_emulate_report_luns [rhel-7.0])

* Thu Nov 28 2013 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-20.el7
- kvm-pc-drop-virtio-balloon-pci-event_idx-compat-property.patch [bz#1029539]
- kvm-virtio-net-only-delete-bh-that-existed.patch [bz#922463]
- kvm-virtio-net-broken-RX-filtering-logic-fixed.patch [bz#1029370]
- kvm-block-Avoid-unecessary-drv-bdrv_getlength-calls.patch [bz#1025138]
- kvm-block-Round-up-total_sectors.patch [bz#1025138]
- kvm-doc-fix-hardcoded-helper-path.patch [bz#1016952]
- kvm-introduce-RFQDN_REDHAT-RHEL-6-7-fwd.patch [bz#971933]
- kvm-error-reason-in-BLOCK_IO_ERROR-BLOCK_JOB_ERROR-event.patch [bz#971938]
- kvm-improve-debuggability-of-BLOCK_IO_ERROR-BLOCK_JOB_ER.patch [bz#895041]
- kvm-vfio-pci-Fix-multifunction-on.patch [bz#1029275]
- kvm-qcow2-Change-default-for-new-images-to-compat-1.1.patch [bz#1026739]
- kvm-qcow2-change-default-for-new-images-to-compat-1.1-pa.patch [bz#1026739]
- kvm-rng-egd-offset-the-point-when-repeatedly-read-from-t.patch [bz#1032862]
- kvm-Fix-rhel-rhev-conflict-for-qemu-kvm-common.patch [bz#1033463]
- Resolves: bz#1016952
  (qemu-kvm man page guide wrong path for qemu-bridge-helper)
- Resolves: bz#1025138
  (Read/Randread/Randrw performance regression)
- Resolves: bz#1026739
  (qcow2: Switch to compat=1.1 default for new images)
- Resolves: bz#1029275
  (Guest only find one 82576 VF(function 0) while use multifunction)
- Resolves: bz#1029370
  ([whql][netkvm][wlk] Virtio-net device handles RX multicast filtering improperly)
- Resolves: bz#1029539
  (Machine type rhel6.1.0 and  balloon device cause migration fail from RHEL6.5 host to RHEL7.0 host)
- Resolves: bz#1032862
  (virtio-rng-egd: repeatedly read same random data-block w/o considering the buffer offset)
- Resolves: bz#1033463
  (can not upgrade qemu-kvm-common to qemu-kvm-common-rhev due to conflicts)
- Resolves: bz#895041
  (QMP: forward port I/O error debug messages)
- Resolves: bz#922463
  (qemu-kvm core dump when virtio-net multi queue guest hot-unpluging vNIC)
- Resolves: bz#971933
  (QMP: add RHEL's vendor extension prefix)
- Resolves: bz#971938
  (QMP: Add error reason to BLOCK_IO_ERROR event)

* Mon Nov 11 2013 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-19.el7
- kvm-qapi-qapi-visit.py-fix-list-handling-for-union-types.patch [bz#848203]
- kvm-qapi-qapi-visit.py-native-list-support.patch [bz#848203]
- kvm-qapi-enable-generation-of-native-list-code.patch [bz#848203]
- kvm-net-add-support-of-mac-programming-over-macvtap-in-Q.patch [bz#848203]
- Resolves: bz#848203
  (MAC Programming for virtio over macvtap - qemu-kvm support)

* Fri Nov 08 2013 Michal Novotny <minovotn@redhat.com> - 1.5.3-18.el7
- Removing leaked patch kvm-e1000-rtl8139-update-HMP-NIC-when-every-bit-is-writt.patch

* Thu Nov 07 2013 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-17.el7
- kvm-pci-assign-Add-MSI-affinity-support.patch [bz#1025877]
- kvm-Fix-potential-resource-leak-missing-fclose.patch [bz#1025877]
- kvm-pci-assign-remove-the-duplicate-function-name-in-deb.patch [bz#1025877]
- kvm-Remove-s390-ccw-img-loader.patch [bz#1017682]
- kvm-Fix-vscclient-installation.patch [bz#1017681]
- kvm-Change-qemu-bridge-helper-permissions-to-4755.patch [bz#1017689]
- kvm-net-update-nic-info-during-device-reset.patch [bz#922589]
- kvm-net-e1000-update-network-information-when-macaddr-is.patch [bz#922589]
- kvm-net-rtl8139-update-network-information-when-macaddr-.patch [bz#922589]
- kvm-virtio-net-fix-up-HMP-NIC-info-string-on-reset.patch [bz#1026689]
- kvm-vfio-pci-VGA-quirk-update.patch [bz#1025477]
- kvm-vfio-pci-Add-support-for-MSI-affinity.patch [bz#1025477]
- kvm-vfio-pci-Test-device-reset-capabilities.patch [bz#1026550]
- kvm-vfio-pci-Lazy-PCI-option-ROM-loading.patch [bz#1026550]
- kvm-vfio-pci-Cleanup-error_reports.patch [bz#1026550]
- kvm-vfio-pci-Add-dummy-PCI-ROM-write-accessor.patch [bz#1026550]
- kvm-vfio-pci-Fix-endian-issues-in-vfio_pci_size_rom.patch [bz#1026550]
- kvm-linux-headers-Update-to-include-vfio-pci-hot-reset-s.patch [bz#1025472]
- kvm-vfio-pci-Implement-PCI-hot-reset.patch [bz#1025472]
- kvm-linux-headers-Update-for-KVM-VFIO-device.patch [bz#1025474]
- kvm-vfio-pci-Make-use-of-new-KVM-VFIO-device.patch [bz#1025474]
- kvm-vmdk-Fix-vmdk_parse_extents.patch [bz#995866]
- kvm-vmdk-fix-VMFS-extent-parsing.patch [bz#995866]
- kvm-e1000-rtl8139-update-HMP-NIC-when-every-bit-is-writt.patch [bz#922589]
- kvm-don-t-disable-ctrl_mac_addr-feature-for-6.5-machine-.patch [bz#1005039]
- Resolves: bz#1005039
  (add compat property to disable ctrl_mac_addr feature)
- Resolves: bz#1017681
  (rpmdiff test "Multilib regressions": vscclient is a libtool script on s390/s390x/ppc/ppc64)
- Resolves: bz#1017682
  (/usr/share/qemu-kvm/s390-ccw.img need not be distributed)
- Resolves: bz#1017689
  (/usr/libexec/qemu-bridge-helper permissions should be 4755)
- Resolves: bz#1025472
  (Nvidia GPU device assignment - qemu-kvm - bus reset support)
- Resolves: bz#1025474
  (Nvidia GPU device assignment - qemu-kvm - NoSnoop support)
- Resolves: bz#1025477
  (VFIO MSI affinity)
- Resolves: bz#1025877
  (pci-assign lacks MSI affinity support)
- Resolves: bz#1026550
  (QEMU VFIO update ROM loading code)
- Resolves: bz#1026689
  (virtio-net: macaddr is reset but network info of monitor isn't updated)
- Resolves: bz#922589
  (e1000/rtl8139: qemu mac address can not be changed via set the hardware address in guest)
- Resolves: bz#995866
  (fix vmdk support to ESX images)

* Thu Nov 07 2013 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-16.el7
- kvm-block-drop-bs_snapshots-global-variable.patch [bz#1026524]
- kvm-block-move-snapshot-code-in-block.c-to-block-snapsho.patch [bz#1026524]
- kvm-block-fix-vvfat-error-path-for-enable_write_target.patch [bz#1026524]
- kvm-block-Bugfix-format-and-snapshot-used-in-drive-optio.patch [bz#1026524]
- kvm-iscsi-use-bdrv_new-instead-of-stack-structure.patch [bz#1026524]
- kvm-qcow2-Add-corrupt-bit.patch [bz#1004347]
- kvm-qcow2-Metadata-overlap-checks.patch [bz#1004347]
- kvm-qcow2-Employ-metadata-overlap-checks.patch [bz#1004347]
- kvm-qcow2-refcount-Move-OFLAG_COPIED-checks.patch [bz#1004347]
- kvm-qcow2-refcount-Repair-OFLAG_COPIED-errors.patch [bz#1004347]
- kvm-qcow2-refcount-Repair-shared-refcount-blocks.patch [bz#1004347]
- kvm-qcow2_check-Mark-image-consistent.patch [bz#1004347]
- kvm-qemu-iotests-Overlapping-cluster-allocations.patch [bz#1004347]
- kvm-w32-Fix-access-to-host-devices-regression.patch [bz#1026524]
- kvm-add-qemu-img-convert-n-option-skip-target-volume-cre.patch [bz#1026524]
- kvm-bdrv-Use-Error-for-opening-images.patch [bz#1026524]
- kvm-bdrv-Use-Error-for-creating-images.patch [bz#1026524]
- kvm-block-Error-parameter-for-open-functions.patch [bz#1026524]
- kvm-block-Error-parameter-for-create-functions.patch [bz#1026524]
- kvm-qemu-img-create-Emit-filename-on-error.patch [bz#1026524]
- kvm-qcow2-Use-Error-parameter.patch [bz#1026524]
- kvm-qemu-iotests-Adjustments-due-to-error-propagation.patch [bz#1026524]
- kvm-block-raw-Employ-error-parameter.patch [bz#1026524]
- kvm-block-raw-win32-Employ-error-parameter.patch [bz#1026524]
- kvm-blkdebug-Employ-error-parameter.patch [bz#1026524]
- kvm-blkverify-Employ-error-parameter.patch [bz#1026524]
- kvm-block-raw-posix-Employ-error-parameter.patch [bz#1026524]
- kvm-block-raw-win32-Always-use-errno-in-hdev_open.patch [bz#1026524]
- kvm-qmp-Documentation-for-BLOCK_IMAGE_CORRUPTED.patch [bz#1004347]
- kvm-qcow2-Correct-snapshots-size-for-overlap-check.patch [bz#1004347]
- kvm-qcow2-CHECK_OFLAG_COPIED-is-obsolete.patch [bz#1004347]
- kvm-qcow2-Correct-endianness-in-overlap-check.patch [bz#1004347]
- kvm-qcow2-Switch-L1-table-in-a-single-sequence.patch [bz#1004347]
- kvm-qcow2-Use-pread-for-inactive-L1-in-overlap-check.patch [bz#1004347]
- kvm-qcow2-Remove-wrong-metadata-overlap-check.patch [bz#1004347]
- kvm-qcow2-Use-negated-overflow-check-mask.patch [bz#1004347]
- kvm-qcow2-Make-overlap-check-mask-variable.patch [bz#1004347]
- kvm-qcow2-Add-overlap-check-options.patch [bz#1004347]
- kvm-qcow2-Array-assigning-options-to-OL-check-bits.patch [bz#1004347]
- kvm-qcow2-Add-more-overlap-check-bitmask-macros.patch [bz#1004347]
- kvm-qcow2-Evaluate-overlap-check-options.patch [bz#1004347]
- kvm-qapi-types.py-Split-off-generate_struct_fields.patch [bz#978402]
- kvm-qapi-types.py-Fix-enum-struct-sizes-on-i686.patch [bz#978402]
- kvm-qapi-types-visit.py-Pass-whole-expr-dict-for-structs.patch [bz#978402]
- kvm-qapi-types-visit.py-Inheritance-for-structs.patch [bz#978402]
- kvm-blockdev-Introduce-DriveInfo.enable_auto_del.patch [bz#978402]
- kvm-Implement-qdict_flatten.patch [bz#978402]
- kvm-blockdev-blockdev-add-QMP-command.patch [bz#978402]
- kvm-blockdev-Separate-ID-generation-from-DriveInfo-creat.patch [bz#978402]
- kvm-blockdev-Pass-QDict-to-blockdev_init.patch [bz#978402]
- kvm-blockdev-Move-parsing-of-media-option-to-drive_init.patch [bz#978402]
- kvm-blockdev-Move-parsing-of-if-option-to-drive_init.patch [bz#978402]
- kvm-blockdev-Moving-parsing-of-geometry-options-to-drive.patch [bz#978402]
- kvm-blockdev-Move-parsing-of-boot-option-to-drive_init.patch [bz#978402]
- kvm-blockdev-Move-bus-unit-index-processing-to-drive_ini.patch [bz#978402]
- kvm-blockdev-Move-virtio-blk-device-creation-to-drive_in.patch [bz#978402]
- kvm-blockdev-Remove-IF_-check-for-read-only-blockdev_ini.patch [bz#978402]
- kvm-qemu-iotests-Check-autodel-behaviour-for-device_del.patch [bz#978402]
- kvm-blockdev-Remove-media-parameter-from-blockdev_init.patch [bz#978402]
- kvm-blockdev-Don-t-disable-COR-automatically-with-blockd.patch [bz#978402]
- kvm-blockdev-blockdev_init-error-conversion.patch [bz#978402]
- kvm-sd-Avoid-access-to-NULL-BlockDriverState.patch [bz#978402]
- kvm-blockdev-fix-cdrom-read_only-flag.patch [bz#978402]
- kvm-block-fix-backing-file-overriding.patch [bz#978402]
- kvm-block-Disable-BDRV_O_COPY_ON_READ-for-the-backing-fi.patch [bz#978402]
- kvm-block-Don-t-copy-backing-file-name-on-error.patch [bz#978402]
- kvm-qemu-iotests-Try-creating-huge-qcow2-image.patch [bz#980771]
- kvm-block-move-qmp-and-info-dump-related-code-to-block-q.patch [bz#980771]
- kvm-block-dump-snapshot-and-image-info-to-specified-outp.patch [bz#980771]
- kvm-block-add-snapshot-info-query-function-bdrv_query_sn.patch [bz#980771]
- kvm-block-add-image-info-query-function-bdrv_query_image.patch [bz#980771]
- kvm-qmp-add-ImageInfo-in-BlockDeviceInfo-used-by-query-b.patch [bz#980771]
- kvm-vmdk-Implement-.bdrv_has_zero_init.patch [bz#980771]
- kvm-qemu-iotests-Add-basic-ability-to-use-binary-sample-.patch [bz#980771]
- kvm-qemu-iotests-Quote-TEST_IMG-and-TEST_DIR-usage.patch [bz#980771]
- kvm-qemu-iotests-fix-test-case-059.patch [bz#980771]
- kvm-qapi-Add-ImageInfoSpecific-type.patch [bz#980771]
- kvm-block-Add-bdrv_get_specific_info.patch [bz#980771]
- kvm-block-qapi-Human-readable-ImageInfoSpecific-dump.patch [bz#980771]
- kvm-qcow2-Add-support-for-ImageInfoSpecific.patch [bz#980771]
- kvm-qemu-iotests-Discard-specific-info-in-_img_info.patch [bz#980771]
- kvm-qemu-iotests-Additional-info-from-qemu-img-info.patch [bz#980771]
- kvm-vmdk-convert-error-code-to-use-errp.patch [bz#980771]
- kvm-vmdk-refuse-enabling-zeroed-grain-with-flat-images.patch [bz#980771]
- kvm-qapi-Add-optional-field-compressed-to-ImageInfo.patch [bz#980771]
- kvm-vmdk-Only-read-cid-from-image-file-when-opening.patch [bz#980771]
- kvm-vmdk-Implment-bdrv_get_specific_info.patch [bz#980771]
- Resolves: bz#1004347
  (Backport qcow2 corruption prevention patches)
- Resolves: bz#1026524
  (Backport block layer error parameter patches)
- Resolves: bz#978402
  ([RFE] Add discard support to qemu-kvm layer)
- Resolves: bz#980771
  ([RFE]  qemu-img should be able to tell the compat version of a qcow2 image)

* Thu Nov 07 2013 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-15.el7
- kvm-cow-make-reads-go-at-a-decent-speed.patch [bz#989646]
- kvm-cow-make-writes-go-at-a-less-indecent-speed.patch [bz#989646]
- kvm-cow-do-not-call-bdrv_co_is_allocated.patch [bz#989646]
- kvm-block-keep-bs-total_sectors-up-to-date-even-for-grow.patch [bz#989646]
- kvm-block-make-bdrv_co_is_allocated-static.patch [bz#989646]
- kvm-block-do-not-use-total_sectors-in-bdrv_co_is_allocat.patch [bz#989646]
- kvm-block-remove-bdrv_is_allocated_above-bdrv_co_is_allo.patch [bz#989646]
- kvm-block-expect-errors-from-bdrv_co_is_allocated.patch [bz#989646]
- kvm-block-Fix-compiler-warning-Werror-uninitialized.patch [bz#989646]
- kvm-qemu-img-always-probe-the-input-image-for-allocated-.patch [bz#989646]
- kvm-block-make-bdrv_has_zero_init-return-false-for-copy-.patch [bz#989646]
- kvm-block-introduce-bdrv_get_block_status-API.patch [bz#989646]
- kvm-block-define-get_block_status-return-value.patch [bz#989646]
- kvm-block-return-get_block_status-data-and-flags-for-for.patch [bz#989646]
- kvm-block-use-bdrv_has_zero_init-to-return-BDRV_BLOCK_ZE.patch [bz#989646]
- kvm-block-return-BDRV_BLOCK_ZERO-past-end-of-backing-fil.patch [bz#989646]
- kvm-qemu-img-add-a-map-subcommand.patch [bz#989646]
- kvm-docs-qapi-document-qemu-img-map.patch [bz#989646]
- kvm-raw-posix-return-get_block_status-data-and-flags.patch [bz#989646]
- kvm-raw-posix-report-unwritten-extents-as-zero.patch [bz#989646]
- kvm-block-add-default-get_block_status-implementation-fo.patch [bz#989646]
- kvm-block-look-for-zero-blocks-in-bs-file.patch [bz#989646]
- kvm-qemu-img-fix-invalid-JSON.patch [bz#989646]
- kvm-block-get_block_status-set-pnum-0-on-error.patch [bz#989646]
- kvm-block-get_block_status-avoid-segfault-if-there-is-no.patch [bz#989646]
- kvm-block-get_block_status-avoid-redundant-callouts-on-r.patch [bz#989646]
- kvm-qcow2-Restore-total_sectors-value-in-save_vmstate.patch [bz#1025740]
- kvm-qcow2-Unset-zero_beyond_eof-in-save_vmstate.patch [bz#1025740]
- kvm-qemu-iotests-Test-for-loading-VM-state-from-qcow2.patch [bz#1025740]
- kvm-apic-rename-apic-specific-bitopts.patch [bz#1001216]
- kvm-hw-import-bitmap-operations-in-qdev-core-header.patch [bz#1001216]
- kvm-qemu-help-Sort-devices-by-logical-functionality.patch [bz#1001216]
- kvm-devices-Associate-devices-to-their-logical-category.patch [bz#1001216]
- kvm-Mostly-revert-qemu-help-Sort-devices-by-logical-func.patch [bz#1001216]
- kvm-qdev-monitor-Group-device_add-help-and-info-qdm-by-c.patch [bz#1001216]
- kvm-qdev-Replace-no_user-by-cannot_instantiate_with_devi.patch [bz#1001216]
- kvm-sysbus-Set-cannot_instantiate_with_device_add_yet.patch [bz#1001216]
- kvm-cpu-Document-why-cannot_instantiate_with_device_add_.patch [bz#1001216]
- kvm-apic-Document-why-cannot_instantiate_with_device_add.patch [bz#1001216]
- kvm-pci-host-Consistently-set-cannot_instantiate_with_de.patch [bz#1001216]
- kvm-ich9-Document-why-cannot_instantiate_with_device_add.patch [bz#1001216]
- kvm-piix3-piix4-Clean-up-use-of-cannot_instantiate_with_.patch [bz#1001216]
- kvm-vt82c686-Clean-up-use-of-cannot_instantiate_with_dev.patch [bz#1001216]
- kvm-isa-Clean-up-use-of-cannot_instantiate_with_device_a.patch [bz#1001216]
- kvm-qdev-Do-not-let-the-user-try-to-device_add-when-it-c.patch [bz#1001216]
- kvm-rhel-Revert-unwanted-cannot_instantiate_with_device_.patch [bz#1001216]
- kvm-rhel-Revert-downstream-changes-to-unused-default-con.patch [bz#1001076]
- kvm-rhel-Drop-cfi.pflash01-and-isa-ide-device.patch [bz#1001076]
- kvm-rhel-Drop-isa-vga-device.patch [bz#1001088]
- kvm-rhel-Make-isa-cirrus-vga-device-unavailable.patch [bz#1001088]
- kvm-rhel-Make-ccid-card-emulated-device-unavailable.patch [bz#1001123]
- kvm-x86-fix-migration-from-pre-version-12.patch [bz#1005695]
- kvm-x86-cpuid-reconstruct-leaf-0Dh-data.patch [bz#1005695]
- kvm-kvmvapic-Catch-invalid-ROM-size.patch [bz#920021]
- kvm-kvmvapic-Enter-inactive-state-on-hardware-reset.patch [bz#920021]
- kvm-kvmvapic-Clear-also-physical-ROM-address-when-enteri.patch [bz#920021]
- kvm-block-optionally-disable-live-block-jobs.patch [bz#987582]
- kvm-rpm-spec-template-disable-live-block-ops-for-rhel-en.patch [bz#987582]
- kvm-migration-disable-live-block-migration-b-i-for-rhel-.patch [bz#1022392]
- kvm-Build-ceph-rbd-only-for-rhev.patch [bz#987583]
- kvm-spec-Disable-host-cdrom-RHEL-only.patch [bz#760885]
- kvm-rhel-Make-pci-serial-2x-and-pci-serial-4x-device-una.patch [bz#1001180]
- kvm-usb-host-libusb-Fix-reset-handling.patch [bz#980415]
- kvm-usb-host-libusb-Configuration-0-may-be-a-valid-confi.patch [bz#980383]
- kvm-usb-host-libusb-Detach-kernel-drivers-earlier.patch [bz#980383]
- kvm-monitor-Remove-pci_add-command-for-Red-Hat-Enterpris.patch [bz#1010858]
- kvm-monitor-Remove-pci_del-command-for-Red-Hat-Enterpris.patch [bz#1010858]
- kvm-monitor-Remove-usb_add-del-commands-for-Red-Hat-Ente.patch [bz#1010858]
- kvm-monitor-Remove-host_net_add-remove-for-Red-Hat-Enter.patch [bz#1010858]
- kvm-fw_cfg-add-API-to-find-FW-cfg-object.patch [bz#990601]
- kvm-pvpanic-use-FWCfgState-explicitly.patch [bz#990601]
- kvm-pvpanic-initialization-cleanup.patch [bz#990601]
- kvm-pvpanic-fix-fwcfg-for-big-endian-hosts.patch [bz#990601]
- kvm-hw-misc-make-pvpanic-known-to-user.patch [bz#990601]
- kvm-gdbstub-do-not-restart-crashed-guest.patch [bz#990601]
- kvm-gdbstub-fix-for-commit-87f25c12bfeaaa0c41fb857713bbc.patch [bz#990601]
- kvm-vl-allow-cont-from-panicked-state.patch [bz#990601]
- kvm-hw-misc-don-t-create-pvpanic-device-by-default.patch [bz#990601]
- kvm-block-vhdx-add-migration-blocker.patch [bz#1007176]
- kvm-qemu-kvm.spec-add-vhdx-to-the-read-only-block-driver.patch [bz#1007176]
- kvm-qemu-kvm.spec-Add-VPC-VHD-driver-to-the-block-read-o.patch [bz#1007176]
- Resolves: bz#1001076
  (Disable or remove other block devices we won't support)
- Resolves: bz#1001088
  (Disable or remove display devices we won't support)
- Resolves: bz#1001123
  (Disable or remove device ccid-card-emulated)
- Resolves: bz#1001180
  (Disable or remove devices pci-serial-2x, pci-serial-4x)
- Resolves: bz#1001216
  (Fix no_user or provide another way make devices unavailable with -device / device_add)
- Resolves: bz#1005695
  (QEMU should hide CPUID.0Dh values that it does not support)
- Resolves: bz#1007176
  (Add VPC and VHDX file formats as supported in qemu-kvm (read-only))
- Resolves: bz#1010858
  (Disable unused human monitor commands)
- Resolves: bz#1022392
  (Disable live-storage-migration in qemu-kvm (migrate -b/-i))
- Resolves: bz#1025740
  (Saving VM state on qcow2 images results in VM state corruption)
- Resolves: bz#760885
  (Disable host cdrom passthrough)
- Resolves: bz#920021
  (qemu-kvm segment fault when reboot guest after hot unplug device with option ROM)
- Resolves: bz#980383
  (The usb3.0 stick can't be returned back to host after shutdown guest with usb3.0 pass-through)
- Resolves: bz#980415
  (libusbx: error [_open_sysfs_attr] open /sys/bus/usb/devices/4-1/bConfigurationValue failed ret=-1 errno=2)
- Resolves: bz#987582
  (Initial Virtualization Differentiation for RHEL7 (Live snapshots))
- Resolves: bz#987583
  (Initial Virtualization Differentiation for RHEL7 (Ceph enablement))
- Resolves: bz#989646
  (Support backup vendors in qemu to access qcow disk readonly)
- Resolves: bz#990601
  (pvpanic device triggers guest bugs when present by default)

* Wed Nov 06 2013 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-14.el7
- kvm-target-i386-remove-tabs-from-target-i386-cpu.h.patch [bz#928867]
- kvm-migrate-vPMU-state.patch [bz#928867]
- kvm-blockdev-do-not-default-cache.no-flush-to-true.patch [bz#1009993]
- kvm-virtio-blk-do-not-relay-a-previous-driver-s-WCE-conf.patch [bz#1009993]
- kvm-rng-random-use-error_setg_file_open.patch [bz#907743]
- kvm-block-mirror_complete-use-error_setg_file_open.patch [bz#907743]
- kvm-blockdev-use-error_setg_file_open.patch [bz#907743]
- kvm-cpus-use-error_setg_file_open.patch [bz#907743]
- kvm-dump-qmp_dump_guest_memory-use-error_setg_file_open.patch [bz#907743]
- kvm-savevm-qmp_xen_save_devices_state-use-error_setg_fil.patch [bz#907743]
- kvm-block-bdrv_reopen_prepare-don-t-use-QERR_OPEN_FILE_F.patch [bz#907743]
- kvm-qerror-drop-QERR_OPEN_FILE_FAILED-macro.patch [bz#907743]
- kvm-rhel-Drop-ivshmem-device.patch [bz#787463]
- kvm-usb-remove-old-usb-host-code.patch [bz#1001144]
- kvm-Add-rhel6-pxe-roms-files.patch [bz#997702]
- kvm-Add-rhel6-pxe-rom-to-redhat-rpm.patch [bz#997702]
- kvm-Fix-migration-from-rhel6.5-to-rhel7-with-ipxe.patch [bz#997702]
- kvm-pc-Don-t-prematurely-explode-QEMUMachineInitArgs.patch [bz#994490]
- kvm-pc-Don-t-explode-QEMUMachineInitArgs-into-local-vari.patch [bz#994490]
- kvm-smbios-Normalize-smbios_entry_add-s-error-handling-t.patch [bz#994490]
- kvm-smbios-Convert-to-QemuOpts.patch [bz#994490]
- kvm-smbios-Improve-diagnostics-for-conflicting-entries.patch [bz#994490]
- kvm-smbios-Make-multiple-smbios-type-accumulate-sanely.patch [bz#994490]
- kvm-smbios-Factor-out-smbios_maybe_add_str.patch [bz#994490]
- kvm-hw-Pass-QEMUMachine-to-its-init-method.patch [bz#994490]
- kvm-smbios-Set-system-manufacturer-product-version-by-de.patch [bz#994490]
- kvm-smbios-Decouple-system-product-from-QEMUMachine.patch [bz#994490]
- kvm-rhel-SMBIOS-type-1-branding.patch [bz#994490]
- kvm-Add-disable-rhev-features-option-to-configure.patch []
- Resolves: bz#1001144
  (Disable or remove device usb-host-linux)
- Resolves: bz#1009993
  (RHEL7 guests do not issue fdatasyncs on virtio-blk)
- Resolves: bz#787463
  (disable ivshmem (was: [Hitachi 7.0 FEAT] Support ivshmem (Inter-VM Shared Memory)))
- Resolves: bz#907743
  (qemu-ga: empty reason string for OpenFileFailed error)
- Resolves: bz#928867
  (Virtual PMU support during live migration - qemu-kvm)
- Resolves: bz#994490
  (Set per-machine-type SMBIOS strings)
- Resolves: bz#997702
  (Migration from RHEL6.5 host to RHEL7.0 host is failed with virtio-net device)

* Tue Nov 05 2013 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-13.el7
- kvm-seabios-paravirt-allow-more-than-1TB-in-x86-guest.patch [bz#989677]
- kvm-scsi-prefer-UUID-to-VM-name-for-the-initiator-name.patch [bz#1006468]
- kvm-Fix-incorrect-rhel_rhev_conflicts-macro-usage.patch [bz#1017693]
- Resolves: bz#1006468
  (libiscsi initiator name should use vm UUID)
- Resolves: bz#1017693
  (incorrect use of rhel_rhev_conflicts)
- Resolves: bz#989677
  ([HP 7.0 FEAT]: Increase KVM guest supported memory to 4TiB)

* Mon Nov 04 2013 Michal Novotny <minovotn@redhat.com> - 1.5.3-12.el7
- kvm-vl-Clean-up-parsing-of-boot-option-argument.patch [bz#997817]
- kvm-qemu-option-check_params-is-now-unused-drop-it.patch [bz#997817]
- kvm-vl-Fix-boot-order-and-once-regressions-and-related-b.patch [bz#997817]
- kvm-vl-Rename-boot_devices-to-boot_order-for-consistency.patch [bz#997817]
- kvm-pc-Make-no-fd-bootchk-stick-across-boot-order-change.patch [bz#997817]
- kvm-doc-Drop-ref-to-Bochs-from-no-fd-bootchk-documentati.patch [bz#997817]
- kvm-libqtest-Plug-fd-and-memory-leaks-in-qtest_quit.patch [bz#997817]
- kvm-libqtest-New-qtest_end-to-go-with-qtest_start.patch [bz#997817]
- kvm-qtest-Don-t-reset-on-qtest-chardev-connect.patch [bz#997817]
- kvm-boot-order-test-New-covering-just-PC-for-now.patch [bz#997817]
- kvm-qemu-ga-execute-fsfreeze-freeze-in-reverse-order-of-.patch [bz#1019352]
- kvm-rbd-link-and-load-librbd-dynamically.patch [bz#989608]
- kvm-rbd-Only-look-for-qemu-specific-copy-of-librbd.so.1.patch [bz#989608]
- kvm-spec-Whitelist-rbd-block-driver.patch [bz#989608]
- Resolves: bz#1019352
  (qemu-guest-agent: "guest-fsfreeze-freeze" deadlocks if the guest have mounted disk images)
- Resolves: bz#989608
  ([7.0 FEAT] qemu runtime support for librbd backend (ceph))
- Resolves: bz#997817
  (-boot order and -boot once regressed since RHEL-6)

* Thu Oct 31 2013 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-11.el7
- kvm-chardev-fix-pty_chr_timer.patch [bz#994414]
- kvm-qemu-socket-zero-initialize-SocketAddress.patch [bz#922010]
- kvm-qemu-socket-drop-pointless-allocation.patch [bz#922010]
- kvm-qemu-socket-catch-monitor_get_fd-failures.patch [bz#922010]
- kvm-qemu-char-check-optional-fields-using-has_.patch [bz#922010]
- kvm-error-add-error_setg_file_open-helper.patch [bz#922010]
- kvm-qemu-char-use-more-specific-error_setg_-variants.patch [bz#922010]
- kvm-qemu-char-print-notification-to-stderr.patch [bz#922010]
- kvm-qemu-char-fix-documentation-for-telnet-wait-socket-f.patch [bz#922010]
- kvm-qemu-char-don-t-leak-opts-on-error.patch [bz#922010]
- kvm-qemu-char-use-ChardevBackendKind-in-CharDriver.patch [bz#922010]
- kvm-qemu-char-minor-mux-chardev-fixes.patch [bz#922010]
- kvm-qemu-char-add-chardev-mux-support.patch [bz#922010]
- kvm-qemu-char-report-udp-backend-errors.patch [bz#922010]
- kvm-qemu-socket-don-t-leak-opts-on-error.patch [bz#922010]
- kvm-chardev-handle-qmp_chardev_add-KIND_MUX-failure.patch [bz#922010]
- kvm-acpi-piix4-Enable-qemu-kvm-compatibility-mode.patch [bz#1019474]
- kvm-target-i386-support-loading-of-cpu-xsave-subsection.patch [bz#1004743]
- Resolves: bz#1004743
  (XSAVE migration format not compatible between RHEL6 and RHEL7)
- Resolves: bz#1019474
  (RHEL-7 can't load piix4_pm migration section from RHEL-6.5)
- Resolves: bz#922010
  (RFE: support hotplugging chardev & serial ports)
- Resolves: bz#994414
  (hot-unplug chardev with pty backend caused qemu Segmentation fault)

* Thu Oct 17 2013 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-10.el7
- kvm-xhci-fix-endpoint-interval-calculation.patch [bz#1001604]
- kvm-xhci-emulate-intr-endpoint-intervals-correctly.patch [bz#1001604]
- kvm-xhci-reset-port-when-disabling-slot.patch [bz#1001604]
- kvm-Revert-usb-hub-report-status-changes-only-once.patch [bz#1001604]
- kvm-target-i386-Set-model-6-on-qemu64-qemu32-CPU-models.patch [bz#1004290]
- kvm-pc-rhel6-doesn-t-have-APIC-on-pentium-CPU-models.patch [bz#918907]
- kvm-pc-RHEL-6-had-x2apic-set-on-Opteron_G-123.patch [bz#918907]
- kvm-pc-RHEL-6-don-t-have-RDTSCP.patch [bz#918907]
- kvm-scsi-Fix-scsi_bus_legacy_add_drive-scsi-generic-with.patch [bz#1009285]
- kvm-seccomp-fine-tuning-whitelist-by-adding-times.patch [bz#1004175]
- kvm-block-add-bdrv_write_zeroes.patch [bz#921465]
- kvm-block-raw-add-bdrv_co_write_zeroes.patch [bz#921465]
- kvm-rdma-export-qemu_fflush.patch [bz#921465]
- kvm-block-migration-efficiently-encode-zero-blocks.patch [bz#921465]
- kvm-Fix-real-mode-guest-migration.patch [bz#921465]
- kvm-Fix-real-mode-guest-segments-dpl-value-in-savevm.patch [bz#921465]
- kvm-migration-add-autoconvergence-documentation.patch [bz#921465]
- kvm-migration-send-total-time-in-QMP-at-completed-stage.patch [bz#921465]
- kvm-migration-don-t-use-uninitialized-variables.patch [bz#921465]
- kvm-pc-drop-external-DSDT-loading.patch [bz#921465]
- kvm-hda-codec-refactor-common-definitions-into-a-header-.patch [bz#954195]
- kvm-hda-codec-make-mixemu-selectable-at-runtime.patch [bz#954195]
- kvm-audio-remove-CONFIG_MIXEMU-configure-option.patch [bz#954195]
- kvm-pc_piix-disable-mixer-for-6.4.0-machine-types-and-be.patch [bz#954195]
- kvm-spec-mixemu-config-option-is-no-longer-supported-and.patch [bz#954195]
- Resolves: bz#1001604
  (usb hub doesn't work properly (win7 sees downstream port #1 only).)
- Resolves: bz#1004175
  ('-sandbox on'  option  cause  qemu-kvm process hang)
- Resolves: bz#1004290
  (Use model 6 for qemu64 and intel cpus)
- Resolves: bz#1009285
  (-device usb-storage,serial=... crashes with SCSI generic drive)
- Resolves: bz#918907
  (provide backwards-compatible RHEL specific machine types in QEMU - CPU features)
- Resolves: bz#921465
  (Migration can not finished even the "remaining ram" is already 0 kb)
- Resolves: bz#954195
  (RHEL machines <=6.4 should not use mixemu)

* Thu Oct 10 2013 Miroslav Rezanina <mrezanin@redhat.com> - 1.5.3-9.el7
- kvm-qxl-fix-local-renderer.patch [bz#1005036]
- kvm-spec-include-userspace-iSCSI-initiator-in-block-driv.patch [bz#923843]
- kvm-linux-headers-update-to-kernel-3.10.0-26.el7.patch [bz#1008987]
- kvm-target-i386-add-feature-kvm_pv_unhalt.patch [bz#1008987]
- kvm-warn-if-num-cpus-is-greater-than-num-recommended.patch [bz#1010881]
- kvm-char-move-backends-io-watch-tag-to-CharDriverState.patch [bz#1007222]
- kvm-char-use-common-function-to-disable-callbacks-on-cha.patch [bz#1007222]
- kvm-char-remove-watch-callback-on-chardev-detach-from-fr.patch [bz#1007222]
- kvm-block-don-t-lose-data-from-last-incomplete-sector.patch [bz#1017049]
- kvm-vmdk-fix-cluster-size-check-for-flat-extents.patch [bz#1017049]
- kvm-qemu-iotests-add-monolithicFlat-creation-test-to-059.patch [bz#1017049]
- Resolves: bz#1005036
  (When using “-vga qxl” together with “-display vnc=:5” or “-display  sdl” qemu displays  pixel garbage)
- Resolves: bz#1007222
  (QEMU core dumped when do hot-unplug virtio serial port during transfer file between host to guest with virtio serial through TCP socket)
- Resolves: bz#1008987
  (pvticketlocks: add kvm feature kvm_pv_unhalt)
- Resolves: bz#1010881
  (backport vcpu soft limit warning)
- Resolves: bz#1017049
  (qemu-img refuses to open the vmdk format image its created)
- Resolves: bz#923843
  (include userspace iSCSI initiator in block driver whitelist)

* Wed Oct 09 2013 Miroslav Rezanina <mrezanin@redhat.com> - qemu-kvm-1.5.3-8.el7
- kvm-vmdk-Make-VMDK3Header-and-VmdkGrainMarker-QEMU_PACKE.patch [bz#995866]
- kvm-vmdk-use-unsigned-values-for-on-disk-header-fields.patch [bz#995866]
- kvm-qemu-iotests-add-poke_file-utility-function.patch [bz#995866]
- kvm-qemu-iotests-add-empty-test-case-for-vmdk.patch [bz#995866]
- kvm-vmdk-check-granularity-field-in-opening.patch [bz#995866]
- kvm-vmdk-check-l2-table-size-when-opening.patch [bz#995866]
- kvm-vmdk-check-l1-size-before-opening-image.patch [bz#995866]
- kvm-vmdk-use-heap-allocation-for-whole_grain.patch [bz#995866]
- kvm-vmdk-rename-num_gtes_per_gte-to-num_gtes_per_gt.patch [bz#995866]
- kvm-vmdk-Move-l1_size-check-into-vmdk_add_extent.patch [bz#995866]
- kvm-vmdk-fix-L1-and-L2-table-size-in-vmdk3-open.patch [bz#995866]
- kvm-vmdk-support-vmfsSparse-files.patch [bz#995866]
- kvm-vmdk-support-vmfs-files.patch [bz#995866]
- Resolves: bz#995866
  (fix vmdk support to ESX images)

* Thu Sep 26 2013 Miroslav Rezanina <mrezanin@redhat.com> - qemu-kvm-1.5.3-7.el7
- kvm-spice-fix-display-initialization.patch [bz#974887]
- kvm-Remove-i82550-network-card-emulation.patch [bz#921983]
- kvm-Remove-usb-wacom-tablet.patch [bz#903914]
- kvm-Disable-usb-uas.patch [bz#903914]
- kvm-Disable-vhost-scsi.patch [bz#994642]
- kvm-Remove-no-hpet-option.patch [bz#947441]
- kvm-Disable-isa-parallel.patch [bz#1002286]
- kvm-xhci-implement-warm-port-reset.patch [bz#949514]
- kvm-usb-add-serial-bus-property.patch [bz#953304]
- kvm-rhel6-compat-usb-serial-numbers.patch [bz#953304]
- kvm-vmdk-fix-comment-for-vmdk_co_write_zeroes.patch [bz#995866]
- kvm-gluster-Add-image-resize-support.patch [bz#1007226]
- kvm-block-Introduce-bs-zero_beyond_eof.patch [bz#1007226]
- kvm-block-Produce-zeros-when-protocols-reading-beyond-en.patch [bz#1007226]
- kvm-gluster-Abort-on-AIO-completion-failure.patch [bz#1007226]
- kvm-Preparation-for-usb-bt-dongle-conditional-build.patch [bz#1001131]
- kvm-Remove-dev-bluetooth.c-dependency-from-vl.c.patch [bz#1001131]
- kvm-exec-Fix-Xen-RAM-allocation-with-unusual-options.patch [bz#1009328]
- kvm-exec-Clean-up-fall-back-when-mem-path-allocation-fai.patch [bz#1009328]
- kvm-exec-Reduce-ifdeffery-around-mem-path.patch [bz#1009328]
- kvm-exec-Simplify-the-guest-physical-memory-allocation-h.patch [bz#1009328]
- kvm-exec-Drop-incorrect-dead-S390-code-in-qemu_ram_remap.patch [bz#1009328]
- kvm-exec-Clean-up-unnecessary-S390-ifdeffery.patch [bz#1009328]
- kvm-exec-Don-t-abort-when-we-can-t-allocate-guest-memory.patch [bz#1009328]
- kvm-pc_sysfw-Fix-ISA-BIOS-init-for-ridiculously-big-flas.patch [bz#1009328]
- kvm-virtio-scsi-Make-type-virtio-scsi-common-abstract.patch [bz#903918]
- kvm-qga-move-logfiles-to-new-directory-for-easier-SELinu.patch [bz#1009491]
- kvm-target-i386-add-cpu64-rhel6-CPU-model.patch [bz#918907]
- kvm-fix-steal-time-MSR-vmsd-callback-to-proper-opaque-ty.patch [bz#903889]
- Resolves: bz#1001131
  (Disable or remove device usb-bt-dongle)
- Resolves: bz#1002286
  (Disable or remove device isa-parallel)
- Resolves: bz#1007226
  (Introduce bs->zero_beyond_eof)
- Resolves: bz#1009328
  ([RFE] Nicer error report when qemu-kvm can't allocate guest RAM)
- Resolves: bz#1009491
  (move qga logfiles to new /var/log/qemu-ga/ directory [RHEL-7])
- Resolves: bz#903889
  (The value of steal time in "top" command always is "0.0% st" after guest migration)
- Resolves: bz#903914
  (Disable or remove usb related devices that we will not support)
- Resolves: bz#903918
  (Disable or remove emulated SCSI devices we will not support)
- Resolves: bz#918907
  (provide backwards-compatible RHEL specific machine types in QEMU - CPU features)
- Resolves: bz#921983
  (Disable or remove emulated network devices that we will not support)
- Resolves: bz#947441
  (HPET device must be disabled)
- Resolves: bz#949514
  (fail to passthrough the USB3.0 stick to windows guest with xHCI controller under pc-i440fx-1.4)
- Resolves: bz#953304
  (Serial number of some USB devices must be fixed for older RHEL machine types)
- Resolves: bz#974887
  (the screen of guest fail to display correctly when use spice + qxl driver)
- Resolves: bz#994642
  (should disable vhost-scsi)
- Resolves: bz#995866
  (fix vmdk support to ESX images)

* Mon Sep 23 2013 Paolo Bonzini <pbonzini@redhat.com> - qemu-kvm-1.5.3-6.el7
- re-enable spice
- Related: #979953

* Mon Sep 23 2013 Paolo Bonzini <pbonzini@redhat.com> - qemu-kvm-1.5.3-5.el7
- temporarily disable spice until libiscsi rebase is complete
- Related: #979953

* Thu Sep 19 2013 Michal Novotny <minovotn@redhat.com> - qemu-kvm-1.5.3-4.el7
- kvm-block-package-preparation-code-in-qmp_transaction.patch [bz#1005818]
- kvm-block-move-input-parsing-code-in-qmp_transaction.patch [bz#1005818]
- kvm-block-package-committing-code-in-qmp_transaction.patch [bz#1005818]
- kvm-block-package-rollback-code-in-qmp_transaction.patch [bz#1005818]
- kvm-block-make-all-steps-in-qmp_transaction-as-callback.patch [bz#1005818]
- kvm-blockdev-drop-redundant-proto_drv-check.patch [bz#1005818]
- kvm-block-Don-t-parse-protocol-from-file.filename.patch [bz#1005818]
- kvm-Revert-block-Disable-driver-specific-options-for-1.5.patch [bz#1005818]
- kvm-qcow2-Add-refcount-update-reason-to-all-callers.patch [bz#1005818]
- kvm-qcow2-Options-to-enable-discard-for-freed-clusters.patch [bz#1005818]
- kvm-qcow2-Batch-discards.patch [bz#1005818]
- kvm-block-Always-enable-discard-on-the-protocol-level.patch [bz#1005818]
- kvm-qapi.py-Avoid-code-duplication.patch [bz#1005818]
- kvm-qapi.py-Allow-top-level-type-reference-for-command-d.patch [bz#1005818]
- kvm-qapi-schema-Use-BlockdevSnapshot-type-for-blockdev-s.patch [bz#1005818]
- kvm-qapi-types.py-Implement-base-for-unions.patch [bz#1005818]
- kvm-qapi-visit.py-Split-off-generate_visit_struct_fields.patch [bz#1005818]
- kvm-qapi-visit.py-Implement-base-for-unions.patch [bz#1005818]
- kvm-docs-Document-QAPI-union-types.patch [bz#1005818]
- kvm-qapi-Add-visitor-for-implicit-structs.patch [bz#1005818]
- kvm-qapi-Flat-unions-with-arbitrary-discriminator.patch [bz#1005818]
- kvm-qapi-Add-consume-argument-to-qmp_input_get_object.patch [bz#1005818]
- kvm-qapi.py-Maintain-a-list-of-union-types.patch [bz#1005818]
- kvm-qapi-qapi-types.py-native-list-support.patch [bz#1005818]
- kvm-qapi-Anonymous-unions.patch [bz#1005818]
- kvm-block-Allow-driver-option-on-the-top-level.patch [bz#1005818]
- kvm-QemuOpts-Add-qemu_opt_unset.patch [bz#1005818]
- kvm-blockdev-Rename-I-O-throttling-options-for-QMP.patch [bz#1005818]
- kvm-qemu-iotests-Update-051-reference-output.patch [bz#1005818]
- kvm-blockdev-Rename-readonly-option-to-read-only.patch [bz#1005818]
- kvm-blockdev-Split-up-cache-option.patch [bz#1005818]
- kvm-qcow2-Use-dashes-instead-of-underscores-in-options.patch [bz#1005818]
- kvm-qemu-iotests-filter-QEMU-version-in-monitor-banner.patch [bz#1006959]
- kvm-tests-set-MALLOC_PERTURB_-to-expose-memory-bugs.patch [bz#1006959]
- kvm-qemu-iotests-Whitespace-cleanup.patch [bz#1006959]
- kvm-qemu-iotests-Fixed-test-case-026.patch [bz#1006959]
- kvm-qemu-iotests-Fix-test-038.patch [bz#1006959]
- kvm-qemu-iotests-Remove-lsi53c895a-tests-from-051.patch [bz#1006959]
- Resolves: bz#1005818
  (qcow2: Backport discard command line options)
- Resolves: bz#1006959
  (qemu-iotests false positives)

* Thu Aug 29 2013 Miroslav Rezanina <mrezanin@redhat.com> - qemu-kvm-1.5.3-3.el7
- Fix rhel/rhev split

* Thu Aug 29 2013 Miroslav Rezanina <mrezanin@redhat.com> - qemu-kvm-1.5.3-2.el7
- kvm-osdep-add-qemu_get_local_state_pathname.patch [bz#964304]
- kvm-qga-determine-default-state-dir-and-pidfile-dynamica.patch [bz#964304]
- kvm-configure-don-t-save-any-fixed-local_statedir-for-wi.patch [bz#964304]
- kvm-qga-create-state-directory-on-win32.patch [bz#964304]
- kvm-qga-save-state-directory-in-ga_install_service-RHEL-.patch [bz#964304]
- kvm-Makefile-create-.-var-run-when-installing-the-POSIX-.patch [bz#964304]
- kvm-qemu-option-Fix-qemu_opts_find-for-null-id-arguments.patch [bz#980782]
- kvm-qemu-option-Fix-qemu_opts_set_defaults-for-corner-ca.patch [bz#980782]
- kvm-vl-New-qemu_get_machine_opts.patch [bz#980782]
- kvm-Fix-machine-options-accel-kernel_irqchip-kvm_shadow_.patch [bz#980782]
- kvm-microblaze-Fix-latent-bug-with-default-DTB-lookup.patch [bz#980782]
- kvm-Simplify-machine-option-queries-with-qemu_get_machin.patch [bz#980782]
- kvm-pci-add-VMSTATE_MSIX.patch [bz#838170]
- kvm-xhci-add-XHCISlot-addressed.patch [bz#838170]
- kvm-xhci-add-xhci_alloc_epctx.patch [bz#838170]
- kvm-xhci-add-xhci_init_epctx.patch [bz#838170]
- kvm-xhci-add-live-migration-support.patch [bz#838170]
- kvm-pc-set-level-xlevel-correctly-on-486-qemu32-CPU-mode.patch [bz#918907]
- kvm-pc-Remove-incorrect-rhel6.x-compat-model-value-for-C.patch [bz#918907]
- kvm-pc-rhel6.x-has-x2apic-present-on-Conroe-Penryn-Nehal.patch [bz#918907]
- kvm-pc-set-compat-CPUID-0x80000001-.EDX-bits-on-Westmere.patch [bz#918907]
- kvm-pc-Remove-PCLMULQDQ-from-Westmere-on-rhel6.x-machine.patch [bz#918907]
- kvm-pc-SandyBridge-rhel6.x-compat-fixes.patch [bz#918907]
- kvm-pc-Haswell-doesn-t-have-rdtscp-on-rhel6.x.patch [bz#918907]
- kvm-i386-fix-LAPIC-TSC-deadline-timer-save-restore.patch [bz#972433]
- kvm-all.c-max_cpus-should-not-exceed-KVM-vcpu-limit.patch [bz#996258]
- kvm-add-timestamp-to-error_report.patch [bz#906937]
- kvm-Convert-stderr-message-calling-error_get_pretty-to-e.patch [bz#906937]
- Resolves: bz#838170
  (Add live migration support for USB [xhci, usb-uas])
- Resolves: bz#906937
  ([Hitachi 7.0 FEAT][QEMU]Add a time stamp to error message (*))
- Resolves: bz#918907
  (provide backwards-compatible RHEL specific machine types in QEMU - CPU features)
- Resolves: bz#964304
  (Windows guest agent service failed to be started)
- Resolves: bz#972433
  ("INFO: rcu_sched detected stalls" after RHEL7 kvm vm migrated)
- Resolves: bz#980782
  (kernel_irqchip defaults to off instead of on without -machine)
- Resolves: bz#996258
  (boot guest with maxcpu=255 successfully but actually max number of vcpu is 160)

* Wed Aug 28 2013 Miroslav Rezanina <mrezanin@redhat.com> - 10:1.5.3-1
- Rebase to qemu 1.5.3

* Tue Aug 20 2013 Miroslav Rezanina <mrezanin@redhat.com> - 10:1.5.2-4
- qemu: guest agent creates files with insecure permissions in deamon mode [rhel-7.0] (rhbz 974444)
- update qemu-ga config & init script in RHEL7 wrt. fsfreeze hook (rhbz 969942)
- RHEL7 does not have equivalent functionality for __com.redhat_qxl_screendump (rhbz 903910)
- SEP flag behavior for CPU models of RHEL6 machine types should be compatible (rhbz 960216)
- crash command can not read the dump-guest-memory file when paging=false [RHEL-7] (rhbz 981582)
- RHEL 7 qemu-kvm fails to build on F19 host due to libusb deprecated API (rhbz 996469)
- Live migration support in virtio-blk-data-plane (rhbz 995030)
- qemu-img resize can execute successfully even input invalid syntax (rhbz 992935)

* Fri Aug 09 2013 Miroslav Rezanina <mrezanin@redhat.com> - 10:1.5.2-3
- query mem info from monitor would cause qemu-kvm hang [RHEL-7] (rhbz #970047)
- Throttle-down guest to help with live migration convergence (backport to RHEL7.0) (rhbz #985958)
- disable (for now) EFI-enabled roms (rhbz #962563)
- qemu-kvm "vPMU passthrough" mode breaks migration, shouldn't be enabled by default (rhbz #853101)
- Remove pending watches after virtserialport unplug (rhbz #992900)
- Containment of error when an SR-IOV device encounters an error... (rhbz #984604)

* Wed Jul 31 2013 Miroslav Rezanina <mrezanin@redhat.com> - 10:1.5.2-2
- SPEC file prepared for RHEL/RHEV split (rhbz #987165)
- RHEL guest( sata disk ) can not boot up (rhbz #981723)
- Kill the "use flash device for BIOS unless KVM" misfeature (rhbz #963280)
- Provide RHEL-6 machine types (rhbz #983991)
- Change s3/s4 default to "disable". (rhbz #980840)
- Support Virtual Memory Disk Format in qemu (rhbz #836675)
- Glusterfs backend for QEMU (rhbz #805139)

* Tue Jul 02 2013 Miroslav Rezanina <mrezanin@redhat.com> - 10:1.5.2-1
- Rebase to 1.5.2

* Tue Jul 02 2013 Miroslav Rezanina <mrezanin@redhat.com> - 10:1.5.1-2
- Fix package package version info (bz #952996)
- pc: Replace upstream machine types by RHEL-7 types (bz #977864)
- target-i386: Update model values on Conroe/Penryn/Nehalem CPU model (bz #861210)
- target-i386: Set level=4 on Conroe/Penryn/Nehalem (bz #861210)

* Fri Jun 28 2013 Miroslav Rezanina <mrezanin@redhat.com> - 10:1.5.1-1
- Rebase to 1.5.1
- Change epoch to 10 to obsolete RHEL-6 qemu-kvm-rhev package (bz #818626)

* Fri May 24 2013 Miroslav Rezanina <mrezanin@redhat.com> - 3:1.5.0-2
- Enable werror (bz #948290)
- Enable nbd driver (bz #875871)
- Fix udev rules file location (bz #958860)
- Remove +x bit from systemd unit files (bz #965000)
- Drop unneeded kvm.modules on x86 (bz #963642)
- Fix build flags
- Enable libusb

* Thu May 23 2013 Miroslav Rezanina <mrezanin@redhat.com> - 3:1.5.0-1
- Rebase to 1.5.0

* Tue Apr 23 2013 Miroslav Rezanina <mrezanin@redhat.com> - 3:1.4.0-4
- Enable build of libcacard subpackage for non-x86_64 archs (bz #873174)
- Enable build of qemu-img subpackage for non-x86_64 archs (bz #873174)
- Enable build of qemu-guest-agent subpackage for non-x86_64 archs (bz #873174)

* Tue Apr 23 2013 Miroslav Rezanina <mrezanin@redhat.com> - 3:1.4.0-3
- Enable/disable features supported by rhel7
- Use qemu-kvm instead of qemu in filenames and pathes

* Fri Apr 19 2013 Daniel Mach <dmach@redhat.com> - 3:1.4.0-2.1
- Rebuild for cyrus-sasl

* Fri Apr 05 2013 Miroslav Rezanina <mrezanin@redhat.com> - 3:1.4.0-2
- Synchronization with Fedora 19 package version 2:1.4.0-8

* Wed Apr 03 2013 Daniel Mach <dmach@redhat.com> - 3:1.4.0-1.1
- Rebuild for libseccomp

* Thu Mar 07 2013 Miroslav Rezanina <mrezanin@redhat.com> - 3:1.4.0-1
- Rebase to 1.4.0

* Mon Feb 25 2013 Michal Novotny <minovotn@redhat.com> - 3:1.3.0-8
- Missing package qemu-system-x86 in hardware certification kvm testing (bz#912433)
- Resolves: bz#912433
  (Missing package qemu-system-x86 in hardware certification kvm testing)

* Fri Feb 22 2013 Alon Levy <alevy@redhat.com> - 3:1.3.0-6
- Bump epoch back to 3 since there has already been a 3 package release:
  3:1.2.0-20.el7 https://brewweb.devel.redhat.com/buildinfo?buildID=244866
- Mark explicit libcacard dependency on new enough qemu-img to avoid conflict
  since /usr/bin/vscclient was moved from qemu-img to libcacard subpackage.

* Wed Feb 13 2013 Michal Novotny <minovotn@redhat.com> - 2:1.3.0-5
- Fix patch contents for usb-redir (bz#895491)
- Resolves: bz#895491
  (PATCH: 0110-usb-redir-Add-flow-control-support.patch has been mangled on rebase !!)

* Wed Feb 06 2013 Alon Levy <alevy@redhat.com> - 2:1.3.0-4
- Add patch from f19 package for libcacard missing error_set symbol.
- Resolves: bz#891552

* Mon Jan 07 2013 Michal Novotny <minovotn@redhat.com> - 2:1.3.0-3
- Remove dependency on bogus qemu-kvm-kvm package [bz#870343]
- Resolves: bz#870343
  (qemu-kvm-1.2.0-16.el7 cant be installed)

* Tue Dec 18 2012 Michal Novotny <minovotn@redhat.com> - 2:1.3.0-2
- Rename qemu to qemu-kvm
- Move qemu-kvm to libexecdir

* Fri Dec 07 2012 Cole Robinson <crobinso@redhat.com> - 2:1.3.0-1
- Switch base tarball from qemu-kvm to qemu
- qemu 1.3 release
- Option to use linux VFIO driver to assign PCI devices
- Many USB3 improvements
- New paravirtualized hardware random number generator device.
- Support for Glusterfs volumes with "gluster://" -drive URI
- Block job commands for live block commit and storage migration

* Wed Nov 28 2012 Alon Levy <alevy@redhat.com> - 2:1.2.0-25
* Merge libcacard into qemu, since they both use the same sources now.

* Thu Nov 22 2012 Paolo Bonzini <pbonzini@redhat.com> - 2:1.2.0-24
- Move vscclient to qemu-common, qemu-nbd to qemu-img

* Tue Nov 20 2012 Alon Levy <alevy@redhat.com> - 2:1.2.0-23
- Rewrite fix for bz #725965 based on fix for bz #867366
- Resolve bz #867366

* Fri Nov 16 2012 Paolo Bonzini <pbonzini@redhat.com> - 2:1.2.0-23
- Backport --with separate_kvm support from EPEL branch

* Fri Nov 16 2012 Paolo Bonzini <pbonzini@redhat.com> - 2:1.2.0-22
- Fix previous commit

* Fri Nov 16 2012 Paolo Bonzini <pbonzini@redhat.com> - 2:1.2.0-21
- Backport commit 38f419f (configure: Fix CONFIG_QEMU_HELPERDIR generation,
  2012-10-17)

* Thu Nov 15 2012 Paolo Bonzini <pbonzini@redhat.com> - 2:1.2.0-20
- Install qemu-bridge-helper as suid root
- Distribute a sample /etc/qemu/bridge.conf file

* Thu Nov  1 2012 Hans de Goede <hdegoede@redhat.com> - 2:1.2.0-19
- Sync spice patches with upstream, minor bugfixes and set the qxl pci
  device revision to 4 by default, so that guests know they can use
  the new features

* Tue Oct 30 2012 Cole Robinson <crobinso@redhat.com> - 2:1.2.0-18
- Fix loading arm initrd if kernel is very large (bz #862766)
- Don't use reserved word 'function' in systemtap files (bz #870972)
- Drop assertion that was triggering when pausing guests w/ qxl (bz
  #870972)

* Sun Oct 28 2012 Cole Robinson <crobinso@redhat.com> - 2:1.2.0-17
- Pull patches queued for qemu 1.2.1

* Fri Oct 19 2012 Paolo Bonzini <pbonzini@redhat.com> - 2:1.2.0-16
- add s390x KVM support
- distribute pre-built firmware or device trees for Alpha, Microblaze, S390
- add missing system targets
- add missing linux-user targets
- fix previous commit

* Thu Oct 18 2012 Dan Horák <dan[at]danny.cz> - 2:1.2.0-15
- fix build on non-kvm arches like s390(x)

* Wed Oct 17 2012 Paolo Bonzini <pbonzini@redhat.com> - 2:1.2.0-14
- Change SLOF Requires for the new version number

* Thu Oct 11 2012 Paolo Bonzini <pbonzini@redhat.com> - 2:1.2.0-13
- Add ppc support to kvm.modules (original patch by David Gibson)
- Replace x86only build with kvmonly build: add separate defines and
  conditionals for all packages, so that they can be chosen and
  renamed in kvmonly builds and so that qemu has the appropriate requires
- Automatically pick libfdt dependancy
- Add knob to disable spice+seccomp

* Fri Sep 28 2012 Paolo Bonzini <pbonzini@redhat.com> - 2:1.2.0-12
- Call udevadm on post, fixing bug 860658

* Fri Sep 28 2012 Hans de Goede <hdegoede@redhat.com> - 2:1.2.0-11
- Rebuild against latest spice-server and spice-protocol
- Fix non-seamless migration failing with vms with usb-redir devices,
  to allow boxes to load such vms from disk

* Tue Sep 25 2012 Hans de Goede <hdegoede@redhat.com> - 2:1.2.0-10
- Sync Spice patchsets with upstream (rhbz#860238)
- Fix building with usbredir >= 0.5.2

* Thu Sep 20 2012 Hans de Goede <hdegoede@redhat.com> - 2:1.2.0-9
- Sync USB and Spice patchsets with upstream

* Sun Sep 16 2012 Richard W.M. Jones <rjones@redhat.com> - 2:1.2.0-8
- Use 'global' instead of 'define', and underscore in definition name,
  n-v-r, and 'dist' tag of SLOF, all to fix RHBZ#855252.

* Fri Sep 14 2012 Paolo Bonzini <pbonzini@redhat.com> - 2:1.2.0-4
- add versioned dependency from qemu-system-ppc to SLOF (BZ#855252)

* Wed Sep 12 2012 Richard W.M. Jones <rjones@redhat.com> - 2:1.2.0-3
- Fix RHBZ#853408 which causes libguestfs failure.

* Sat Sep  8 2012 Hans de Goede <hdegoede@redhat.com> - 2:1.2.0-2
- Fix crash on (seamless) migration
- Sync usbredir live migration patches with upstream

* Fri Sep  7 2012 Hans de Goede <hdegoede@redhat.com> - 2:1.2.0-1
- New upstream release 1.2.0 final
- Add support for Spice seamless migration
- Add support for Spice dynamic monitors
- Add support for usb-redir live migration

* Tue Sep 04 2012 Adam Jackson <ajax@redhat.com> 1.2.0-0.5.rc1
- Flip Requires: ceph >= foo to Conflicts: ceph < foo, so we pull in only the
  libraries which we need and not the rest of ceph which we don't.

* Tue Aug 28 2012 Cole Robinson <crobinso@redhat.com> 1.2.0-0.4.rc1
- Update to 1.2.0-rc1

* Mon Aug 20 2012 Richard W.M. Jones <rjones@redhat.com> - 1.2-0.3.20120806git3e430569
- Backport Bonzini's vhost-net fix (RHBZ#848400).

* Tue Aug 14 2012 Cole Robinson <crobinso@redhat.com> - 1.2-0.2.20120806git3e430569
- Bump release number, previous build forgot but the dist bump helped us out

* Tue Aug 14 2012 Cole Robinson <crobinso@redhat.com> - 1.2-0.1.20120806git3e430569
- Revive qemu-system-{ppc*, sparc*} (bz 844502)
- Enable KVM support for all targets (bz 844503)

* Mon Aug 06 2012 Cole Robinson <crobinso@redhat.com> - 1.2-0.1.20120806git3e430569.fc18
- Update to git snapshot

* Sun Jul 29 2012 Cole Robinson <crobinso@redhat.com> - 1.1.1-1
- Upstream stable release 1.1.1
- Fix systemtap tapsets (bz 831763)
- Fix VNC audio tunnelling (bz 840653)
- Don't renable ksm on update (bz 815156)
- Bump usbredir dep (bz 812097)
- Fix RPM install error on non-virt machines (bz 660629)
- Obsolete openbios to fix upgrade dependency issues (bz 694802)

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2:1.1.0-9
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Tue Jul 10 2012 Richard W.M. Jones <rjones@redhat.com> - 2:1.1.0-8
- Re-diff previous patch so that it applies and actually apply it

* Tue Jul 10 2012 Richard W.M. Jones <rjones@redhat.com> - 2:1.1.0-7
- Add patch to fix default machine options.  This fixes libvirt
  detection of qemu.
- Back out patch 1 which conflicts.

* Fri Jul  6 2012 Hans de Goede <hdegoede@redhat.com> - 2:1.1.0-5
- Fix qemu crashing (on an assert) whenever USB-2.0 isoc transfers are used

* Thu Jul  5 2012 Richard W.M. Jones <rjones@redhat.com> - 2:1.1.0-4
- Disable tests since they hang intermittently.
- Add kvmvapic.bin (replaces vapic.bin).
- Add cpus-x86_64.conf.  qemu now creates /etc/qemu/target-x86_64.conf
  as an empty file.
- Add qemu-icon.bmp.
- Add qemu-bridge-helper.
- Build and include virtfs-proxy-helper + man page (thanks Hans de Goede).

* Wed Jul  4 2012 Hans de Goede <hdegoede@redhat.com> - 2:1.1.0-1
- New upstream release 1.1.0
- Drop about a 100 spice + USB patches, which are all upstream

* Mon Apr 23 2012 Paolo Bonzini <pbonzini@redhat.com> - 2:1.0-17
- Fix install failure due to set -e (rhbz #815272)

* Mon Apr 23 2012 Paolo Bonzini <pbonzini@redhat.com> - 2:1.0-16
- Fix kvm.modules to exit successfully on non-KVM capable systems (rhbz #814932)

* Thu Apr 19 2012 Hans de Goede <hdegoede@redhat.com> - 2:1.0-15
- Add a couple of backported QXL/Spice bugfixes
- Add spice volume control patches

* Fri Apr 6 2012 Paolo Bonzini <pbonzini@redhat.com> - 2:1.0-12
- Add back PPC and SPARC user emulators
- Update binfmt rules from upstream

* Mon Apr  2 2012 Hans de Goede <hdegoede@redhat.com> - 2:1.0-11
- Some more USB bugfixes from upstream

* Thu Mar 29 2012 Eduardo Habkost <ehabkost@redhat.com> - 2:1.0-12
- Fix ExclusiveArch mistake that disabled all non-x86_64 builds on Fedora

* Wed Mar 28 2012 Eduardo Habkost <ehabkost@redhat.com> - 2:1.0-11
- Use --with variables for build-time settings

* Wed Mar 28 2012 Daniel P. Berrange <berrange@redhat.com> - 2:1.0-10
- Switch to use iPXE for netboot ROMs

* Thu Mar 22 2012 Daniel P. Berrange <berrange@redhat.com> - 2:1.0-9
- Remove O_NOATIME for 9p filesystems

* Mon Mar 19 2012 Daniel P. Berrange <berrange@redhat.com> - 2:1.0-8
- Move udev rules to /lib/udev/rules.d (rhbz #748207)

* Fri Mar  9 2012 Hans de Goede <hdegoede@redhat.com> - 2:1.0-7
- Add a whole bunch of USB bugfixes from upstream

* Mon Feb 13 2012 Daniel P. Berrange <berrange@redhat.com> - 2:1.0-6
- Add many more missing BRs for misc QEMU features
- Enable running of test suite during build

* Tue Feb 07 2012 Justin M. Forbes <jforbes@redhat.com> - 2:1.0-5
- Add support for virtio-scsi

* Sun Feb  5 2012 Richard W.M. Jones <rjones@redhat.com> - 2:1.0-4
- Require updated ceph for latest librbd with rbd_flush symbol.

* Tue Jan 24 2012 Justin M. Forbes <jforbes@redhat.com> - 2:1.0-3
- Add support for vPMU
- e1000: bounds packet size against buffer size CVE-2012-0029

* Fri Jan 13 2012 Justin M. Forbes <jforbes@redhat.com> - 2:1.0-2
- Add patches for USB redirect bits
- Remove palcode-clipper, we don't build it

* Wed Jan 11 2012 Justin M. Forbes <jforbes@redhat.com> - 2:1.0-1
- Add patches from 1.0.1 queue

* Fri Dec 16 2011 Justin M. Forbes <jforbes@redhat.com> - 2:1.0-1
- Update to qemu 1.0

* Tue Nov 15 2011 Justin M. Forbes <jforbes@redhat.com> - 2:0.15.1-3
- Enable spice for i686 users as well

* Thu Nov 03 2011 Justin M. Forbes <jforbes@redhat.com> - 2:0.15.1-2
- Fix POSTIN scriplet failure (#748281)

* Fri Oct 21 2011 Justin M. Forbes <jforbes@redhat.com> - 2:0.15.1-1
- Require seabios-bin >= 0.6.0-2 (#741992)
- Replace init scripts with systemd units (#741920)
- Update to 0.15.1 stable upstream

* Fri Oct 21 2011 Paul Moore <pmoore@redhat.com>
- Enable full relro and PIE (rhbz #738812)

* Wed Oct 12 2011 Daniel P. Berrange <berrange@redhat.com> - 2:0.15.0-6
- Add BR on ceph-devel to enable RBD block device

* Wed Oct  5 2011 Daniel P. Berrange <berrange@redhat.com> - 2:0.15.0-5
- Create a qemu-guest-agent sub-RPM for guest installation

* Tue Sep 13 2011 Daniel P. Berrange <berrange@redhat.com> - 2:0.15.0-4
- Enable DTrace tracing backend for SystemTAP (rhbz #737763)
- Enable build with curl (rhbz #737006)

* Thu Aug 18 2011 Hans de Goede <hdegoede@redhat.com> - 2:0.15.0-3
- Add missing BuildRequires: usbredir-devel, so that the usbredir code
  actually gets build

* Thu Aug 18 2011 Richard W.M. Jones <rjones@redhat.com> - 2:0.15.0-2
- Add upstream qemu patch 'Allow to leave type on default in -machine'
  (2645c6dcaf6ea2a51a3b6dfa407dd203004e4d11).

* Sun Aug 14 2011 Justin M. Forbes <jforbes@redhat.com> - 2:0.15.0-1
- Update to 0.15.0 stable release.

* Thu Aug 04 2011 Justin M. Forbes <jforbes@redhat.com> - 2:0.15.0-0.3.201108040af4922
- Update to 0.15.0-rc1 as we prepare for 0.15.0 release

* Thu Aug  4 2011 Daniel P. Berrange <berrange@redhat.com> - 2:0.15.0-0.3.2011072859fadcc
- Fix default accelerator for non-KVM builds (rhbz #724814)

* Thu Jul 28 2011 Justin M. Forbes <jforbes@redhat.com> - 2:0.15.0-0.1.2011072859fadcc
- Update to 0.15.0-rc0 as we prepare for 0.15.0 release

* Tue Jul 19 2011 Hans de Goede <hdegoede@redhat.com> - 2:0.15.0-0.2.20110718525e3df
- Add support usb redirection over the network, see:
  http://fedoraproject.org/wiki/Features/UsbNetworkRedirection
- Restore chardev flow control patches

* Mon Jul 18 2011 Justin M. Forbes <jforbes@redhat.com> - 2:0.15.0-0.1.20110718525e3df
- Update to git snapshot as we prepare for 0.15.0 release

* Wed Jun 22 2011 Richard W.M. Jones <rjones@redhat.com> - 2:0.14.0-9
- Add BR libattr-devel.  This caused the -fstype option to be disabled.
  https://www.redhat.com/archives/libvir-list/2011-June/thread.html#01017

* Mon May  2 2011 Hans de Goede <hdegoede@redhat.com> - 2:0.14.0-8
- Fix a bug in the spice flow control patches which breaks the tcp chardev

* Tue Mar 29 2011 Justin M. Forbes <jforbes@redhat.com> - 2:0.14.0-7
- Disable qemu-ppc and qemu-sparc packages (#679179)

* Mon Mar 28 2011 Justin M. Forbes <jforbes@redhat.com> - 2:0.14.0-6
- Spice fixes for flow control.

* Tue Mar 22 2011 Dan Horák <dan[at]danny.cz> - 2:0.14.0-5
- be more careful when removing the -g flag on s390

* Fri Mar 18 2011 Justin M. Forbes <jforbes@redhat.com> - 2:0.14.0-4
- Fix thinko on adding the most recent patches.

* Wed Mar 16 2011 Justin M. Forbes <jforbes@redhat.com> - 2:0.14.0-3
- Fix migration issue with vhost
- Fix qxl locking issues for spice

* Wed Mar 02 2011 Justin M. Forbes <jforbes@redhat.com> - 2:0.14.0-2
- Re-enable sparc and cris builds

* Thu Feb 24 2011 Justin M. Forbes <jforbes@redhat.com> - 2:0.14.0-1
- Update to 0.14.0 release

* Fri Feb 11 2011 Justin M. Forbes <jforbes@redhat.com> - 2:0.14.0-0.1.20110210git7aa8c46
- Update git snapshot
- Temporarily disable qemu-cris and qemu-sparc due to build errors (to be resolved shorly)

* Tue Feb 08 2011 Justin M. Forbes <jforbes@redhat.com> - 2:0.14.0-0.1.20110208git3593e6b
- Update to 0.14.0 rc git snapshot
- Add virtio-net to modules

* Wed Nov  3 2010 Daniel P. Berrange <berrange@redhat.com> - 2:0.13.0-2
- Revert previous change
- Make qemu-common own the /etc/qemu directory
- Add /etc/qemu/target-x86_64.conf to qemu-system-x86 regardless
  of host architecture.

* Wed Nov 03 2010 Dan Horák <dan[at]danny.cz> - 2:0.13.0-2
- Remove kvm config file on non-x86 arches (part of #639471)
- Own the /etc/qemu directory

* Mon Oct 18 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.13.0-1
- Update to 0.13.0 upstream release
- Fixes for vhost
- Fix mouse in certain guests (#636887)
- Fix issues with WinXP guest install (#579348)
- Resolve build issues with S390 (#639471)
- Fix Windows XP on Raw Devices (#631591)

* Tue Oct 05 2010 jkeating - 2:0.13.0-0.7.rc1.1
- Rebuilt for gcc bug 634757

* Tue Sep 21 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.13.0-0.7.rc1
- Flip qxl pci id from unstable to stable (#634535)
- KSM Fixes from upstream (#558281)

* Tue Sep 14 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.13.0-0.6.rc1
- Move away from git snapshots as 0.13 is close to release
- Updates for spice 0.6

* Tue Aug 10 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.13.0-0.5.20100809git25fdf4a
- Fix typo in e1000 gpxe rom requires.
- Add links to newer vgabios

* Tue Aug 10 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.13.0-0.4.20100809git25fdf4a
- Disable spice on 32bit, it is not supported and buildreqs don't exist.

* Mon Aug 9 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.13.0-0.3.20100809git25fdf4a
- Updates from upstream towards 0.13 stable
- Fix requires on gpxe
- enable spice now that buildreqs are in the repository.
- ksmtrace has moved to a separate upstream package

* Tue Jul 27 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.13.0-0.2.20100727gitb81fe95
- add texinfo buildreq for manpages.

* Tue Jul 27 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.13.0-0.1.20100727gitb81fe95
- Update to 0.13.0 upstream snapshot
- ksm init fixes from upstream

* Tue Jul 20 2010 Dan Horák <dan[at]danny.cz> - 2:0.12.3-8
- Add avoid-llseek patch from upstream needed for building on s390(x)
- Don't use parallel make on s390(x)

* Tue Jun 22 2010 Amit Shah <amit.shah@redhat.com> - 2:0.12.3-7
- Add vvfat hardening patch from upstream (#605202)

* Fri Apr 23 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.12.3-6
- Change requires to the noarch seabios-bin
- Add ownership of docdir to qemu-common (#572110)
- Fix "Cannot boot from non-existent NIC" error when using virt-install (#577851)

* Thu Apr 15 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.12.3-5
- Update virtio console patches from upstream

* Thu Mar 11 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.12.3-4
- Detect cdrom via ioctl (#473154)
- re add increased buffer for USB control requests (#546483)

* Wed Mar 10 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.12.3-3
- Migration clear the fd in error cases (#518032)

* Tue Mar 09 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.12.3-2
- Allow builds --with x86only
- Add libaio-devel buildreq for aio support

* Fri Feb 26 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.12.3-1
- Update to 0.12.3 upstream
- vhost-net migration/restart fixes
- Add F-13 machine type
- virtio-serial fixes

* Tue Feb 09 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.12.2-6
- Add vhost net support.

* Thu Feb 04 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.12.2-5
- Avoid creating too large iovecs in multiwrite merge (#559717)
- Don't try to set max_kernel_pages during ksm init on newer kernels (#558281)
- Add logfile options for ksmtuned debug.

* Wed Jan 27 2010 Amit Shah <amit.shah@redhat.com> - 2:0.12.2-4
- Remove build dependency on iasl now that we have seabios

* Wed Jan 27 2010 Amit Shah <amit.shah@redhat.com> - 2:0.12.2-3
- Remove source target for 0.12.1.2

* Wed Jan 27 2010 Amit Shah <amit.shah@redhat.com> - 2:0.12.2-2
- Add virtio-console patches from upstream for the F13 VirtioSerial feature

* Mon Jan 25 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.12.2-1
- Update to 0.12.2 upstream

* Sun Jan 10 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.12.1.2-3
- Point to seabios instead of bochs, and add a requires for seabios

* Mon Jan  4 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.12.1.2-2
- Remove qcow2 virtio backing file patch

* Mon Jan  4 2010 Justin M. Forbes <jforbes@redhat.com> - 2:0.12.1.2-1
- Update to 0.12.1.2 upstream
- Remove patches included in upstream

* Fri Nov 20 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.11.0-12
- Fix a use-after-free crasher in the slirp code (#539583)
- Fix overflow in the parallels image format support (#533573)

* Wed Nov  4 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.11.0-11
- Temporarily disable preadv/pwritev support to fix data corruption (#526549)

* Tue Nov  3 2009 Justin M. Forbes <jforbes@redhat.com> - 2:0.11.0-10
- Default ksm and ksmtuned services on.

* Thu Oct 29 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.11.0-9
- Fix dropped packets with non-virtio NICs (#531419)

* Wed Oct 21 2009 Glauber Costa <gcosta@redhat.com> - 2:0.11.0-8
- Properly save kvm time registers (#524229)

* Mon Oct 19 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.11.0-7
- Fix potential segfault from too small MSR_COUNT (#528901)

* Fri Oct  9 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.11.0-6
- Fix fs errors with virtio and qcow2 backing file (#524734)
- Fix ksm initscript errors on kernel missing ksm (#527653)
- Add missing Requires(post): getent, useradd, groupadd (#527087)

* Tue Oct  6 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.11.0-5
- Add 'retune' verb to ksmtuned init script

* Mon Oct  5 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.11.0-4
- Use rtl8029 PXE rom for ne2k_pci, not ne (#526777)
- Also, replace the gpxe-roms-qemu pkg requires with file-based requires

* Thu Oct  1 2009 Justin M. Forbes <jmforbes@redhat.com> - 2:0.11.0-3
- Improve error reporting on file access (#524695)

* Mon Sep 28 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.11.0-2
- Fix pci hotplug to not exit if supplied an invalid NIC model (#524022)

* Mon Sep 28 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.11.0-1
- Update to 0.11.0 release
- Drop a couple of upstreamed patches

* Wed Sep 23 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.92-5
- Fix issue causing NIC hotplug confusion when no model is specified (#524022)

* Wed Sep 16 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.92-4
- Fix for KSM patch from Justin Forbes

* Wed Sep 16 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.92-3
- Add ksmtuned, also from Dan Kenigsberg
- Use %%_initddir macro

* Wed Sep 16 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.92-2
- Add ksm control script from Dan Kenigsberg

* Mon Sep  7 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.92-1
- Update to qemu-kvm-0.11.0-rc2
- Drop upstreamed patches
- extboot install now fixed upstream
- Re-place TCG init fix (#516543) with the one gone upstream

* Mon Sep  7 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.91-0.10.rc1
- Fix MSI-X error handling on older kernels (#519787)

* Fri Sep  4 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.91-0.9.rc1
- Make pulseaudio the default audio backend (#519540, #495964, #496627)

* Thu Aug 20 2009 Richard W.M. Jones <rjones@redhat.com> - 2:0.10.91-0.8.rc1
- Fix segfault when qemu-kvm is invoked inside a VM (#516543)

* Tue Aug 18 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.91-0.7.rc1
- Fix permissions on udev rules (#517571)

* Mon Aug 17 2009 Lubomir Rintel <lkundrak@v3.sk> - 2:0.10.91-0.6.rc1
- Allow blacklisting of kvm modules (#517866)

* Fri Aug  7 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.91-0.5.rc1
- Fix virtio_net with -net user (#516022)

* Tue Aug  4 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.91-0.4.rc1
- Update to qemu-kvm-0.11-rc1; no changes from rc1-rc0

* Tue Aug  4 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.91-0.3.rc1.rc0
- Fix extboot checksum (bug #514899)

* Fri Jul 31 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.91-0.2.rc1.rc0
- Add KSM support
- Require bochs-bios >= 2.3.8-0.8 for latest kvm bios updates

* Thu Jul 30 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.91-0.1.rc1.rc0
- Update to qemu-kvm-0.11.0-rc1-rc0
- This is a pre-release of the official -rc1
- A vista installer regression is blocking the official -rc1 release
- Drop qemu-prefer-sysfs-for-usb-host-devices.patch
- Drop qemu-fix-build-for-esd-audio.patch
- Drop qemu-slirp-Fix-guestfwd-for-incoming-data.patch
- Add patch to ensure extboot.bin is installed

* Sun Jul 26 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2:0.10.50-14.kvm88
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Thu Jul 23 2009 Glauber Costa <glommer@redhat.com> - 2:0.10.50-13.kvm88
- Fix bug 513249, -net channel option is broken

* Thu Jul 16 2009 Daniel P. Berrange <berrange@redhat.com> - 2:0.10.50-12.kvm88
- Add 'qemu' user and group accounts
- Force disable xen until it can be made to build

* Thu Jul 16 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.50-11.kvm88
- Update to kvm-88, see http://www.linux-kvm.org/page/ChangeLog
- Package mutiboot.bin
- Update for how extboot is built
- Fix sf.net source URL
- Drop qemu-fix-ppc-softmmu-kvm-disabled-build.patch
- Drop qemu-fix-pcspk-build-with-kvm-disabled.patch
- Cherry-pick fix for esound support build failure

* Wed Jul 15 2009 Daniel Berrange <berrange@lettuce.camlab.fab.redhat.com> - 2:0.10.50-10.kvm87
- Add udev rules to make /dev/kvm world accessible & group=kvm (rhbz #497341)
- Create a kvm group if it doesn't exist (rhbz #346151)

* Tue Jul 07 2009 Glauber Costa <glommer@redhat.com> - 2:0.10.50-9.kvm87
- use pxe roms from gpxe, instead of etherboot package.

* Fri Jul  3 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.50-8.kvm87
- Prefer sysfs over usbfs for usb passthrough (#508326)

* Sat Jun 27 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.50-7.kvm87
- Update to kvm-87
- Drop upstreamed patches
- Cherry-pick new ppc build fix from upstream
- Work around broken linux-user build on ppc
- Fix hw/pcspk.c build with --disable-kvm
- Re-enable preadv()/pwritev() since #497429 is long since fixed
- Kill petalogix-s3adsp1800.dtb, since we don't ship the microblaze target

* Fri Jun  5 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.50-6.kvm86
- Fix 'kernel requires an x86-64 CPU' error
- BuildRequires ncurses-devel to enable '-curses' option (#504226)

* Wed Jun  3 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.50-5.kvm86
- Prevent locked cdrom eject - fixes hang at end of anaconda installs (#501412)
- Avoid harmless 'unhandled wrmsr' warnings (#499712)

* Thu May 21 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.50-4.kvm86
- Update to kvm-86 release
- ChangeLog here: http://marc.info/?l=kvm&m=124282885729710

* Fri May  1 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.50-3.kvm85
- Really provide qemu-kvm as a metapackage for comps

* Tue Apr 28 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.50-2.kvm85
- Provide qemu-kvm as a metapackage for comps

* Mon Apr 27 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10.50-1.kvm85
- Update to qemu-kvm-devel-85
- kvm-85 is based on qemu development branch, currently version 0.10.50
- Include new qemu-io utility in qemu-img package
- Re-instate -help string for boot=on to fix virtio booting with libvirt
- Drop upstreamed patches
- Fix missing kernel/include/asm symlink in upstream tarball
- Fix target-arm build
- Fix build on ppc
- Disable preadv()/pwritev() until bug #497429 is fixed
- Kill more .kernelrelease uselessness
- Make non-kvm qemu build verbose

* Fri Apr 24 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10-15
- Fix source numbering typos caused by make-release addition

* Thu Apr 23 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10-14
- Improve instructions for generating the tarball

* Tue Apr 21 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10-13
- Enable pulseaudio driver to fix qemu lockup at shutdown (#495964)

* Tue Apr 21 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10-12
- Another qcow2 image corruption fix (#496642)

* Mon Apr 20 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10-11
- Fix qcow2 image corruption (#496642)

* Sun Apr 19 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10-10
- Run sysconfig.modules from %%post on x86_64 too (#494739)

* Sun Apr 19 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10-9
- Align VGA ROM to 4k boundary - fixes 'qemu-kvm -std vga' (#494376)

* Tue Apr  14 2009 Glauber Costa <glommer@redhat.com> - 2:0.10-8
- Provide qemu-kvm conditional on the architecture.

* Thu Apr  9 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10-7
- Add a much cleaner fix for vga segfault (#494002)

* Sun Apr  5 2009 Glauber Costa <glommer@redhat.com> - 2:0.10-6
- Fixed qcow2 segfault creating disks over 2TB. #491943

* Fri Apr  3 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10-5
- Fix vga segfault under kvm-autotest (#494002)
- Kill kernelrelease hack; it's not needed
- Build with "make V=1" for more verbose logs

* Thu Apr 02 2009 Glauber Costa <glommer@redhat.com> - 2:0.10-4
- Support botting gpxe roms.

* Wed Apr 01 2009 Glauber Costa <glommer@redhat.com> - 2:0.10-2
- added missing patch. love for CVS.

* Wed Apr 01 2009 Glauber Costa <glommer@redhat.com> - 2:0.10-1
- Include debuginfo for qemu-img
- Do not require qemu-common for qemu-img
- Explicitly own each of the firmware files
- remove firmwares for ppc and sparc. They should be provided by an external package.
  Not that the packages exists for sparc in the secondary arch repo as noarch, but they
  don't automatically get into main repos. Unfortunately it's the best we can do right
  now.
- rollback a bit in time. Snapshot from avi's maint/2.6.30
  - this requires the sasl patches to come back.
  - with-patched-kernel comes back.

* Wed Mar 25 2009 Mark McLoughlin <markmc@redhat.com> - 2:0.10-0.12.kvm20090323git
- BuildRequires pciutils-devel for device assignment (#492076)

* Mon Mar 23 2009 Glauber Costa <glommer@redhat.com> - 2:0.10-0.11.kvm20090323git
- Update to snapshot kvm20090323.
- Removed patch2 (upstream).
- use upstream's new split package.
- --with-patched-kernel flag not needed anymore
- Tell how to get the sources.

* Wed Mar 18 2009 Glauber Costa <glommer@redhat.com> - 2:0.10-0.10.kvm20090310git
- Added extboot to files list.

* Wed Mar 11 2009 Glauber Costa <glommer@redhat.com> - 2:0.10-0.9.kvm20090310git
- Fix wrong reference to bochs bios.

* Wed Mar 11 2009 Glauber Costa <glommer@redhat.com> - 2:0.10-0.8.kvm20090310git
- fix Obsolete/Provides pair
- Use kvm bios from bochs-bios package.
- Using RPM_OPT_FLAGS in configure
- Picked back audio-drv-list from kvm package

* Tue Mar 10 2009 Glauber Costa <glommer@redhat.com> - 2:0.10-0.7.kvm20090310git
- modify ppc patch

* Tue Mar 10 2009 Glauber Costa <glommer@redhat.com> - 2:0.10-0.6.kvm20090310git
- updated to kvm20090310git
- removed sasl patches (already in this release)

* Tue Mar 10 2009 Glauber Costa <glommer@redhat.com> - 2:0.10-0.5.kvm20090303git
- kvm.modules were being wrongly mentioned at %%install.
- update description for the x86 system package to include kvm support
- build kvm's own bios. It is still necessary while kvm uses a slightly different
  irq routing mechanism

* Thu Mar 05 2009 Glauber Costa <glommer@redhat.com> - 2:0.10-0.4.kvm20090303git
- seems Epoch does not go into the tags. So start back here.

* Thu Mar 05 2009 Glauber Costa <glommer@redhat.com> - 2:0.10-0.1.kvm20090303git
- Use bochs-bios instead of bochs-bios-data
- It's official: upstream set on 0.10

* Thu Mar  5 2009 Daniel P. Berrange <berrange@redhat.com> - 2:0.9.2-0.2.kvm20090303git
- Added BSD to license list, since many files are covered by BSD

* Wed Mar 04 2009 Glauber Costa <glommer@redhat.com> - 0.9.2-0.1.kvm20090303git
- missing a dot. shame on me

* Wed Mar 04 2009 Glauber Costa <glommer@redhat.com> - 0.92-0.1.kvm20090303git
- Set Epoch to 2
- Set version to 0.92. It seems upstream keep changing minds here, so pick the lowest
- Provides KVM, Obsoletes KVM
- Only install qemu-kvm in ix86 and x86_64
- Remove pkgdesc macros, as they were generating bogus output for rpm -qi.
- fix ppc and ppc64 builds

* Tue Mar 03 2009 Glauber Costa <glommer@redhat.com> - 0.10-0.3.kvm20090303git
- only execute post scripts for user package.
- added kvm tools.

* Tue Mar 03 2009 Glauber Costa <glommer@redhat.com> - 0.10-0.2.kvm20090303git
- put kvm.modules into cvs

* Tue Mar 03 2009 Glauber Costa <glommer@redhat.com> - 0.10-0.1.kvm20090303git
- Set Epoch to 1
- Build KVM (basic build, no tools yet)
- Set ppc in ExcludeArch. This is temporary, just to fix one issue at a time.
  ppc users (IBM ? ;-)) please wait a little bit.

* Tue Mar  3 2009 Daniel P. Berrange <berrange@redhat.com> - 1.0-0.5.svn6666
- Support VNC SASL authentication protocol
- Fix dep on bochs-bios-data

* Tue Mar 03 2009 Glauber Costa <glommer@redhat.com> - 1.0-0.4.svn6666
- use bios from bochs-bios package.

* Tue Mar 03 2009 Glauber Costa <glommer@redhat.com> - 1.0-0.3.svn6666
- use vgabios from vgabios package.

* Mon Mar 02 2009 Glauber Costa <glommer@redhat.com> - 1.0-0.2.svn6666
- use pxe roms from etherboot package.

* Mon Mar 02 2009 Glauber Costa <glommer@redhat.com> - 1.0-0.1.svn6666
- Updated to tip svn (release 6666). Featuring split packages for qemu.
  Unfortunately, still using binary blobs for the bioses.

* Wed Feb 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.9.1-13
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Sun Jan 11 2009 Debarshi Ray <rishi@fedoraproject.org> - 0.9.1-12
- Updated build patch. Closes Red Hat Bugzilla bug #465041.

* Wed Dec 31 2008 Dennis Gilmore <dennis@ausil.us> - 0.9.1-11
- add sparcv9 and sparc64 support

* Fri Jul 25 2008 Bill Nottingham <notting@redhat.com>
- Fix qemu-img summary (#456344)

* Wed Jun 25 2008 Daniel P. Berrange <berrange@redhat.com> - 0.9.1-10.fc10
- Rebuild for GNU TLS ABI change

* Wed Jun 11 2008 Daniel P. Berrange <berrange@redhat.com> - 0.9.1-9.fc10
- Remove bogus wildcard from files list (rhbz #450701)

* Sat May 17 2008 Lubomir Rintel <lkundrak@v3.sk> - 0.9.1-8
- Register binary handlers also for shared libraries

* Mon May  5 2008 Daniel P. Berrange <berrange@redhat.com> - 0.9.1-7.fc10
- Fix text console PTYs to be in rawmode

* Sun Apr 27 2008 Lubomir Kundrak <lkundrak@redhat.com> - 0.9.1-6
- Register binary handler for SuperH-4 CPU

* Wed Mar 19 2008 Daniel P. Berrange <berrange@redhat.com> - 0.9.1-5.fc9
- Split qemu-img tool into sub-package for smaller footprint installs

* Wed Feb 27 2008 Daniel P. Berrange <berrange@redhat.com> - 0.9.1-4.fc9
- Fix block device checks for extendable disk formats (rhbz #435139)

* Sat Feb 23 2008 Daniel P. Berrange <berrange@redhat.com> - 0.9.1-3.fc9
- Fix block device extents check (rhbz #433560)

* Mon Feb 18 2008 Fedora Release Engineering <rel-eng@fedoraproject.org> - 0.9.1-2
- Autorebuild for GCC 4.3

* Tue Jan  8 2008 Daniel P. Berrange <berrange@redhat.com> - 0.9.1-1.fc9
- Updated to 0.9.1 release
- Fix license tag syntax
- Don't mark init script as a config file

* Wed Sep 26 2007 Daniel P. Berrange <berrange@redhat.com> - 0.9.0-5.fc8
- Fix rtl8139 checksum calculation for Vista (rhbz #308201)

* Tue Aug 28 2007 Daniel P. Berrange <berrange@redhat.com> - 0.9.0-4.fc8
- Fix debuginfo by passing -Wl,--build-id to linker

* Tue Aug 28 2007 David Woodhouse <dwmw2@infradead.org> 0.9.0-4
- Update licence
- Fix CDROM emulation (#253542)

* Tue Aug 28 2007 Daniel P. Berrange <berrange@redhat.com> - 0.9.0-3.fc8
- Added backport of VNC password auth, and TLS+x509 cert auth
- Switch to rtl8139 NIC by default for linkstate reporting
- Fix rtl8139 mmio region mappings with multiple NICs

* Sun Apr  1 2007 Hans de Goede <j.w.r.degoede@hhs.nl> 0.9.0-2
- Fix direct loading of a linux kernel with -kernel & -initrd (bz 234681)
- Remove spurious execute bits from manpages (bz 222573)

* Tue Feb  6 2007 David Woodhouse <dwmw2@infradead.org> 0.9.0-1
- Update to 0.9.0

* Wed Jan 31 2007 David Woodhouse <dwmw2@infradead.org> 0.8.2-5
- Include licences

* Mon Nov 13 2006 Hans de Goede <j.w.r.degoede@hhs.nl> 0.8.2-4
- Backport patch to make FC6 guests work by Kevin Kofler
  <Kevin@tigcc.ticalc.org> (bz 207843).

* Mon Sep 11 2006 David Woodhouse <dwmw2@infradead.org> 0.8.2-3
- Rebuild

* Thu Aug 24 2006 Matthias Saou <http://freshrpms.net/> 0.8.2-2
- Remove the target-list iteration for x86_64 since they all build again.
- Make gcc32 vs. gcc34 conditional on %%{fedora} to share the same spec for
  FC5 and FC6.

* Wed Aug 23 2006 Matthias Saou <http://freshrpms.net/> 0.8.2-1
- Update to 0.8.2 (#200065).
- Drop upstreamed syscall-macros patch2.
- Put correct scriplet dependencies.
- Force install mode for the init script to avoid umask problems.
- Add %%postun condrestart for changes to the init script to be applied if any.
- Update description with the latest "about" from the web page (more current).
- Update URL to qemu.org one like the Source.
- Add which build requirement.
- Don't include texi files in %%doc since we ship them in html.
- Switch to using gcc34 on devel, FC5 still has gcc32.
- Add kernheaders patch to fix linux/compiler.h inclusion.
- Add target-sparc patch to fix compiling on ppc (some int32 to float).

* Thu Jun  8 2006 David Woodhouse <dwmw2@infradead.org> 0.8.1-3
- More header abuse in modify_ldt(), change BuildRoot:

* Wed Jun  7 2006 David Woodhouse <dwmw2@infradead.org> 0.8.1-2
- Fix up kernel header abuse

* Tue May 30 2006 David Woodhouse <dwmw2@infradead.org> 0.8.1-1
- Update to 0.8.1

* Sat Mar 18 2006 David Woodhouse <dwmw2@infradead.org> 0.8.0-6
- Update linker script for PPC

* Sat Mar 18 2006 David Woodhouse <dwmw2@infradead.org> 0.8.0-5
- Just drop $RPM_OPT_FLAGS. They're too much of a PITA

* Sat Mar 18 2006 David Woodhouse <dwmw2@infradead.org> 0.8.0-4
- Disable stack-protector options which gcc 3.2 doesn't like

* Fri Mar 17 2006 David Woodhouse <dwmw2@infradead.org> 0.8.0-3
- Use -mcpu= instead of -mtune= on x86_64 too
- Disable SPARC targets on x86_64, because dyngen doesn't like fnegs

* Fri Mar 17 2006 David Woodhouse <dwmw2@infradead.org> 0.8.0-2
- Don't use -mtune=pentium4 on i386. GCC 3.2 doesn't like it

* Fri Mar 17 2006 David Woodhouse <dwmw2@infradead.org> 0.8.0-1
- Update to 0.8.0
- Resort to using compat-gcc-32
- Enable ALSA

* Mon May 16 2005 David Woodhouse <dwmw2@infradead.org> 0.7.0-2
- Proper fix for GCC 4 putting 'blr' or 'ret' in the middle of the function,
  for i386, x86_64 and PPC.

* Sat Apr 30 2005 David Woodhouse <dwmw2@infradead.org> 0.7.0-1
- Update to 0.7.0
- Fix dyngen for PPC functions which end in unconditional branch

* Thu Apr  7 2005 Michael Schwendt <mschwendt[AT]users.sf.net>
- rebuilt

* Sun Feb 13 2005 David Woodhouse <dwmw2@infradead.org> 0.6.1-2
- Package cleanup

* Sun Nov 21 2004 David Woodhouse <dwmw2@redhat.com> 0.6.1-1
- Update to 0.6.1

* Tue Jul 20 2004 David Woodhouse <dwmw2@redhat.com> 0.6.0-2
- Compile fix from qemu CVS, add x86_64 host support

* Wed May 12 2004 David Woodhouse <dwmw2@redhat.com> 0.6.0-1
- Update to 0.6.0.

* Sat May 8 2004 David Woodhouse <dwmw2@redhat.com> 0.5.5-1
- Update to 0.5.5.

* Sun May 2 2004 David Woodhouse <dwmw2@redhat.com> 0.5.4-1
- Update to 0.5.4.

* Thu Apr 22 2004 David Woodhouse <dwmw2@redhat.com> 0.5.3-1
- Update to 0.5.3. Add init script.

* Thu Jul 17 2003 Jeff Johnson <jbj@redhat.com> 0.4.3-1
- Create.
