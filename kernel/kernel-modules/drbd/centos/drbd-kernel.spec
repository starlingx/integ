%if "%{?_tis_build_type}" == "rt"
%define bt_ext -rt
%else
%undefine bt_ext
%endif

# Define the kmod package name here.
%define kmod_name drbd

Name: drbd-kernel%{?bt_ext}
Summary: Kernel driver for DRBD
Version: 8.4.11
%define upstream_release 1
Release: %{upstream_release}%{?_tis_dist}.%{tis_patch_ver}
%global tarball_version %(echo "%{version}-%{?upstream_release}" | sed -e "s,%{?dist}$,,")
Group: System Environment/Kernel
License: GPLv2+
Summary: %{kmod_name} kernel module(s)

BuildRequires: kernel%{?bt_ext}-devel, redhat-rpm-config, perl, openssl
ExclusiveArch: x86_64

# Sources.
Source0: http://oss.linbit.com/drbd/drbd-%{tarball_version}.tar.gz

# WRS
Patch0001: 0001-remove_bind_before_connect_error.patch

%define kversion %(rpm -q kernel%{?bt_ext}-devel | sort --version-sort | tail -1 | sed 's/kernel%{?bt_ext}-devel-//')

Summary:          drbd kernel module(s)
Group:            System Environment/Kernel
%global _use_internal_dependency_generator 0
Provides:         kernel-modules >= %{kversion}
Provides:         drbd-kernel = %{?epoch:%{epoch}:}%{version}-%{release}
Requires(post):   /usr/sbin/depmod
Requires(postun): /usr/sbin/depmod
BuildRequires: kernel%{?bt_ext}-devel

%description
This module is the kernel-dependent driver for DRBD.  This is split out so
that multiple kernel driver versions can be installed, one for each
installed kernel.

%package       -n kmod-drbd%{?bt_ext}
Summary:          drbd kernel module(s)
%description -n kmod-drbd%{?bt_ext}
This module is the kernel-dependent driver for DRBD.  This is split out so
that multiple kernel driver versions can be installed, one for each
installed kernel.

%post          -n kmod-drbd%{?bt_ext}
echo "Working. This may take some time ..."
if [ -e "/boot/System.map-%{kversion}" ]; then
    /usr/sbin/depmod -aeF "/boot/System.map-%{kversion}" "%{kversion}" > /dev/null || :
fi
modules=( $(find /lib/modules/%{kversion}/extra/drbd | grep '\.ko$') )
if [ -x "/sbin/weak-modules" ]; then
    printf '%s\n' "${modules[@]}" | /sbin/weak-modules --add-modules
fi
echo "Done."
%preun         -n kmod-drbd%{?bt_ext}
rpm -ql kmod-drbd%{?bt_ext}-%{version}-%{release}.x86_64 | grep '\.ko$' > /var/run/rpm-kmod-drbd%{?bt_ext}-modules
%postun        -n kmod-drbd%{?bt_ext}
echo "Working. This may take some time ..."
if [ -e "/boot/System.map-%{kversion}" ]; then
    /usr/sbin/depmod -aeF "/boot/System.map-%{kversion}" "%{kversion}" > /dev/null || :
fi
modules=( $(cat /var/run/rpm-kmod-drbd%{?bt_ext}-modules) )
rm /var/run/rpm-kmod-drbd%{?bt_ext}-modules
if [ -x "/sbin/weak-modules" ]; then
    printf '%s\n' "${modules[@]}" | /sbin/weak-modules --remove-modules
fi
echo "Done."
%files         -n kmod-drbd%{?bt_ext}
%defattr(644,root,root,755)
/lib/modules/%{kversion}/
%config(noreplace)/etc/depmod.d/drbd.conf
%doc /usr/share/doc/kmod-drbd-%{version}/


# Disable the building of the debug package(s).
%define debug_package %{nil}

%prep
%setup -q -n drbd-%{tarball_version}
%patch0001 -p1

%build
rm -rf obj
mkdir obj
ln -s ../scripts obj/
cp -r drbd obj/default
make -C obj/default %{_smp_mflags} all KDIR=/usr/src/kernels/%{kversion}

%install
pwd
%{__install} -d %{buildroot}/lib/modules/%{kversion}/extra/%{kmod_name}/
%{__install} obj/default/%{kmod_name}.ko %{buildroot}/lib/modules/%{kversion}/extra/%{kmod_name}/
%{__install} -d %{buildroot}%{_sysconfdir}/depmod.d/
%{__install} -d %{buildroot}%{_defaultdocdir}/kmod-%{kmod_name}-%{version}/
%{__install} ChangeLog %{buildroot}%{_defaultdocdir}/kmod-%{kmod_name}-%{version}/
%{__install} COPYING %{buildroot}%{_defaultdocdir}/kmod-%{kmod_name}-%{version}/
mv obj/default/.kernel.config.gz obj/k-config-$kernelrelease.gz
%{__install} obj/k-config-$kernelrelease.gz %{buildroot}%{_defaultdocdir}/kmod-%{kmod_name}-%{version}/

echo "override drbd * weak-updates" > %{buildroot}%{_sysconfdir}/depmod.d/drbd.conf 

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
* Wed Dec 16 2015  Philipp Reisner <phil@linbit.com> - 8.4.7-1
- New upstream release.

* Wed Sep 16 2015  Lars Ellenberg <lars@linbit.com> - 8.4.6-5
- New upstream release.

* Thu Jul 30 2015 Lars Ellenberg <lars@linbit.com> - 8.4.6-4
- New upstream release.

* Fri Apr  3 2015 Philipp Reisner <phil@linbit.com> - 8.4.6-1
- New upstream release.

* Mon Jun  2 2014 Philipp Reisner <phil@linbit.com> - 8.4.5-1
- New upstream release.

* Fri Oct 11 2013 Philipp Reisner <phil@linbit.com> - 8.4.4-1
- New upstream release.

* Tue Feb  5 2013 Philipp Reisner <phil@linbit.com> - 8.4.3-1
- New upstream release.

* Thu Sep  6 2012 Philipp Reisner <phil@linbit.com> - 8.4.2-1
- New upstream release.

* Tue Dec 20 2011 Philipp Reisner <phil@linbit.com> - 8.4.1-1
- New upstream release.

* Mon Jul 18 2011 Philipp Reisner <phil@linbit.com> - 8.4.0-1
- New upstream release.

* Fri Jan 28 2011 Philipp Reisner <phil@linbit.com> - 8.3.10-1
- New upstream release.

* Thu Nov 25 2010 Andreas Gruenbacher <agruen@linbit.com> - 8.3.9-1
- Convert to a Kernel Module Package.
