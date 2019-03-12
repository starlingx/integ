%if "%{?_tis_build_type}" == "rt"
%define bt_ext -rt
%else
%undefine bt_ext
%endif

# Define the kmod package name here.
%define kmod_name tpm

Name:    %{kmod_name}-kmod%{?bt_ext}
# the version is the Kernel version from which
# this driver is extracted
Version: 4.12
Release: 0%{?_tis_dist}.%{tis_patch_ver}
Group:   System Environment/Kernel
License: GPLv2
Summary: %{kmod_name}%{?bt_ext} kernel module(s)

BuildRequires: kernel%{?bt_ext}-devel, redhat-rpm-config, perl, openssl
ExclusiveArch: x86_64

# Sources.
# the tpmdd is available as a tarball, with
# the git commit Id referenced in the name
Source0:  %{kmod_name}-kmod-e6aef069.tar.gz
Source1:  modules-load.conf
Source2:  COPYING
Source3:  README

# Patches
Patch01: 0001-disable-arm64-acpi-command.patch
Patch02: 0002-tpmdd-kcompat-support.patch
Patch03: UPSTREAM-0001-tpm-replace-msleep-with-usleep_range.patch
Patch04: UPSTREAM-0002-tpm-reduce-tpm-polling-delay-in-tpm_tis_core.patch
Patch05: UPSTREAM-0003-tpm-use-tpm_msleep-value-as-max-delay.patch
Patch06: UPSTREAM-0004-tpm-wait-for-stat-to-specify-variable-polling-time.patch
Patch07: UPSTREAM-0005-tpm-ignore-burstcount-to-improve-send-performance.patch
Patch08: UPSTREAM-0006-tpm-use-struct-tpm_chip.patch

%define kversion %(rpm -q kernel%{?bt_ext}-devel | sort --version-sort | tail -1 | sed 's/kernel%{?bt_ext}-devel-//')

%package       -n kmod-tpm%{?bt_ext}
Summary:          TPM kernel module(s) and drivers
Group:            System Environment/Kernel
%global _use_internal_dependency_generator 0
Provides:         kernel-modules >= %{kversion}
Provides:         tpm-kmod = %{?epoch:%{epoch}:}%{version}-%{release}
Requires(post):   /usr/sbin/depmod
Requires(postun): /usr/sbin/depmod
%description   -n kmod-tpm%{?bt_ext}
This package provides the %{version} TPM kernel module(s) and drivers built
for the Linux kernel using the %{_target_cpu} family of processors.

%package          symbols
Summary:          Contains the Module.symvers file for this module
Group:            Development/System
%description      symbols      
This package provides the Module.symvers file which will be used
by other dependant Kernel modules, if they use Kernel symbols that
this module exports
%files            symbols
%defattr(-,root,root)
%{_usrsrc}/debug/tpm/Module.symvers


%post          -n kmod-tpm%{?bt_ext}
echo "Working. This may take some time ..."
if [ -e "/boot/System.map-%{kversion}" ]; then
    /usr/sbin/depmod -aeF "/boot/System.map-%{kversion}" "%{kversion}" > /dev/null || :
fi
modules=( $(find /lib/modules/%{kversion}/kernel/drivers/char/tpm | grep '\.ko$') )
if [ -x "/sbin/weak-modules" ]; then
    printf '%s\n' "${modules[@]}" | /sbin/weak-modules --add-modules
fi
echo "Done."

%preun         -n kmod-tpm%{?bt_ext}
rpm -ql kmod-tpm%{?bt_ext}-%{version}-%{release}.x86_64 | grep '\.ko$' > /var/run/rpm-kmod-tpm%{?bt_ext}-modules

%postun        -n kmod-tpm%{?bt_ext}
echo "Working. This may take some time ..."
if [ -e "/boot/System.map-%{kversion}" ]; then
    /usr/sbin/depmod -aeF "/boot/System.map-%{kversion}" "%{kversion}" > /dev/null || :
fi
modules=( $(cat /var/run/rpm-kmod-tpm%{?bt_ext}-modules) )
rm /var/run/rpm-kmod-tpm%{?bt_ext}-modules
if [ -x "/sbin/weak-modules" ]; then
    printf '%s\n' "${modules[@]}" | /sbin/weak-modules --remove-modules
fi
echo "Done."

%files         -n kmod-tpm%{?bt_ext}
%defattr(644,root,root,755)
/lib/modules/%{kversion}/
%doc /usr/share/doc/kmod-tpm/
%{_sysconfdir}/modules-load.d/tpm_tis.conf

# Disable the building of the debug package(s).
%define debug_package %{nil}

%description
This package provides the %{kmod_name} kernel module(s).
It is built to depend upon the specific ABI provided by a range of releases
of the same variant of the Linux kernel and not on any one specific build.

%prep
%autosetup -p 1 -n %{kmod_name}

%build
# build out all the TPM kernel modules
%{__make} KSRC=%{_usrsrc}/kernels/%{kversion}

%install
%{__install} -d %{buildroot}/lib/modules/%{kversion}/kernel/drivers/char/%{kmod_name}/
%{__install} *.ko %{buildroot}/lib/modules/%{kversion}/kernel/drivers/char/%{kmod_name}/

# install the Module.symvers file
%{__install} -d %{buildroot}%{_usrsrc}/debug/%{kmod_name}/
%{__install} Module.symvers %{buildroot}%{_usrsrc}/debug/%{kmod_name}/

%{__install} -d %{buildroot}%{_sysconfdir}/modules-load.d
%{__install} -m 644 %{SOURCE1} %{buildroot}%{_sysconfdir}/modules-load.d/tpm_tis.conf

%{__install} -d %{buildroot}%{_defaultdocdir}/kmod-%{kmod_name}/
%{__install} %{SOURCE2} %{buildroot}%{_defaultdocdir}/kmod-%{kmod_name}/
%{__install} %{SOURCE3} %{buildroot}%{_defaultdocdir}/kmod-%{kmod_name}/

# Strip the modules(s).
find %{buildroot} -type f -name \*.ko -exec %{__strip} --strip-debug \{\} \;

# Always Sign the modules(s).
# If the module signing keys are not defined, define them here.
%{!?privkey: %define privkey /usr/src/kernels/%{kversion}/signing_key.priv}
%{!?pubkey: %define pubkey /usr/src/kernels/%{kversion}/signing_key.x509}
for module in $(find %{buildroot} -type f -name \*.ko);
do %{__perl} /usr/src/kernels/%{kversion}/scripts/sign-file \
    sha256 %{privkey} %{pubkey} $module;
done

%clean
%{__rm} -rf %{buildroot}

%changelog
* Wed Apr 19 2017 Kam Nasim <kam.nasim@windriver.com> 4.12
- Initial RPM package.

