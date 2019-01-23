%if "%{?_tis_build_type}" == "rt"
%define bt_ext -rt
%else
%undefine bt_ext
%endif

# Define the kmod package name here.
%define kmod_name integrity

Name:    %{kmod_name}-kmod%{?bt_ext}
# the version is the Kernel version from which
# this driver is extracted
Version: 4.12
Release: 0%{?_tis_dist}.%{tis_patch_ver}
Group:   System Environment/Kernel
License: GPLv2
Summary: %{kmod_name}%{?bt_ext} kernel module(s)

BuildRequires: kernel%{?bt_ext}-devel, redhat-rpm-config, perl, tpm-kmod%{?bt_ext}-symbols, openssl
ExclusiveArch: x86_64

# Sources.
# the integrity is available as a tarball, with
# the git commit Id referenced in the name
Source0:  %{kmod_name}-kmod-e6aef069.tar.gz
Source1:  modules-load.conf
Source2:  COPYING
Source3:  README
Source4:  integrity.conf
Source5:  ima.conf
Source6:  ima.policy

# Patches
Patch01: 0001-integrity-kcompat-support.patch
Patch02: 0002-integrity-expose-module-params.patch
Patch03: 0003-integrity-restrict-by-iversion.patch
Patch04: 0004-integrity-disable-set-xattr-on-imasig.patch
Patch05: Changes-for-CentOS-7.4-support.patch
Patch06: Changes-for-CentOS-7.6-support.patch

%define kversion %(rpm -q kernel%{?bt_ext}-devel | sort --version-sort | tail -1 | sed 's/kernel%{?bt_ext}-devel-//')

%package       -n kmod-integrity%{?bt_ext}
Summary:          Integrity kernel module(s) and driver
Group:            System Environment/Kernel
%global _use_internal_dependency_generator 0
Provides:         kernel-modules >= %{kversion}
Provides:         integrity-kmod = %{?epoch:%{epoch}:}%{version}-%{release}
Requires(post):   /usr/sbin/depmod
Requires(postun): /usr/sbin/depmod

%description   -n kmod-integrity%{?bt_ext}
This package provides the %{version} Integrity / IMA kernel module(s) and drivers built
for the Linux kernel using the %{_target_cpu} family of processors.

%post          -n kmod-integrity%{?bt_ext}
echo "Working. This may take some time ..."
if [ -e "/boot/System.map-%{kversion}" ]; then
    /usr/sbin/depmod -aeF "/boot/System.map-%{kversion}" "%{kversion}" > /dev/null || :
fi
modules=( $(find /lib/modules/%{kversion}/kernel/security/integrity/ | grep '\.ko$') )
if [ -x "/sbin/weak-modules" ]; then
    printf '%s\n' "${modules[@]}" | /sbin/weak-modules --add-modules
fi
echo "Done."

%preun         -n kmod-integrity%{?bt_ext}
rpm -ql kmod-integrity%{?bt_ext}-%{version}-%{release}.x86_64 | grep '\.ko$' > /var/run/rpm-kmod-integrity%{?bt_ext}-modules

%postun        -n kmod-integrity%{?bt_ext}
echo "Working. This may take some time ..."
if [ -e "/boot/System.map-%{kversion}" ]; then
    /usr/sbin/depmod -aeF "/boot/System.map-%{kversion}" "%{kversion}" > /dev/null || :
fi
modules=( $(cat /var/run/rpm-kmod-integrity%{?bt_ext}-modules) )
rm /var/run/rpm-kmod-integrity%{?bt_ext}-modules
if [ -x "/sbin/weak-modules" ]; then
    printf '%s\n' "${modules[@]}" | /sbin/weak-modules --remove-modules
fi
echo "Done."

%files         -n kmod-integrity%{?bt_ext}
%defattr(-,root,root,-)
/lib/modules/%{kversion}/
%doc /usr/share/doc/kmod-integrity/
%{_sysconfdir}/modules-load.d/ima.conf
%config(noreplace) %{_sysconfdir}/modprobe.d/integrity.conf
%config(noreplace) %{_sysconfdir}/modprobe.d/ima.conf
%{_sysconfdir}/ima.policy

# Disable the building of the debug package(s).
%define debug_package %{nil}

%description
This package provides the %{kmod_name} kernel module(s).
It is built to depend upon the specific ABI provided by a range of releases
of the same variant of the Linux kernel and not on any one specific build.

%prep
%autosetup -p 1 -n %{kmod_name}

%build
# build out all the Integrity / IMA kernel modules
%{__make} KSRC=%{_usrsrc}/kernels/%{kversion} KBUILD_EXTRA_SYMBOLS=%{_usrsrc}/debug/tpm/Module.symvers

%install
%{__install} -d %{buildroot}/lib/modules/%{kversion}/kernel/security/%{kmod_name}/
%{__install} *.ko %{buildroot}/lib/modules/%{kversion}/kernel/security/%{kmod_name}/
%{__install} -d %{buildroot}/lib/modules/%{kversion}/kernel/security/%{kmod_name}/ima/
%{__install} ima/*.ko %{buildroot}/lib/modules/%{kversion}/kernel/security/%{kmod_name}/ima/
%{__install} -d %{buildroot}%{_sysconfdir}/modules-load.d
%{__install} -m 644 %{SOURCE1} %{buildroot}%{_sysconfdir}/modules-load.d/ima.conf
%{__install} -d %{buildroot}%{_sysconfdir}/modprobe.d
%{__install} -p -m 0644 %{SOURCE4} %{buildroot}%{_sysconfdir}/modprobe.d/integrity.conf
%{__install} -p -m 0644 %{SOURCE5} %{buildroot}%{_sysconfdir}/modprobe.d/ima.conf
%{__install} -p -m 0400 %{SOURCE6} %{buildroot}%{_sysconfdir}/ima.policy
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
* Mon Aug 21 2017 Kam Nasim <kam.nasim@windriver.com> 4.12
- Initial RPM package.

