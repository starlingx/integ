%if "%{?_tis_build_type}" == "rt"
%define bt_ext -rt
%else
%undefine bt_ext
%endif

Summary: Intel(r) QuickAssist Technology API
%define pkgname qat17
Name: %{pkgname}%{?bt_ext}
Version: 4.5.0
%define upstream_release 00034
Release: %{upstream_release}%{?_tis_dist}.%{tis_patch_ver}
License: GPLv2
Group: base
Packager: Wind River <info@windriver.com>
URL: https://01.org/packet-processing/intel%C2%AE-quickassist-technology-drivers-and-patches

BuildRequires: kernel%{?bt_ext}-devel
BuildRequires: zlib-devel
BuildRequires: openssl-devel
BuildRequires: pciutils
BuildRequires: libudev-devel
BuildRequires: boost-devel
BuildRequires: perl
BuildRequires: openssl

%define icp_tools accelcomp
%define kernel_version %(rpm -q kernel%{?bt_ext}-devel | sed 's/kernel%{?bt_ext}-devel-//')
%define staging_kernel_dir /usr/src/kernels/%{kernel_version}/
%define qat_unpack_dir %{_builddir}/%{name}-%{version}
%define qat_src_dir %{qat_unpack_dir}

Source: qat1.7.l.%{version}-%{upstream_release}.tar.gz
Source1: qat
# Use our own service script rather than massively patching theirs
Source2: qat_service

#Patch1: 0001-Install-config-file-for-each-VF.patch
Patch2: Get-and-report-the-return-code-on-firmware-load-fail.patch

%description
Intel(r) QuickAssist Technology API

%prep
rm -rf %{qat_unpack_dir}
mkdir -p %{qat_unpack_dir}
cd %{qat_unpack_dir}

gzip -dc %{_sourcedir}/qat1.7.l.%{version}-%{upstream_release}.tar.gz | tar -xvvf -
if [ $? -ne 0 ]; then
  exit $?
fi

#%patch1 -p1
%patch2 -p1

%build

ICP_ROOT=%{qat_src_dir}
KERNEL_SOURCE_ROOT=%{staging_kernel_dir}
mkdir -p %{qat_src_dir}/build
ICP_BUILD_OUTPUT=%{qat_src_dir}/build
export ICP_ROOT KERNEL_SOURCE_ROOT ICP_BUILD_OUTPUT

cd %{qat_src_dir}
%configure --enable-icp-sriov=host

make -C %{qat_src_dir}/

# intel test sample
make -C %{qat_src_dir}/ sample-all

%install

%{__install} -d %{buildroot}%{_sysconfdir}/default
%{__install} -m 750 %SOURCE1 %{buildroot}%{_sysconfdir}/default

%{__install} -d %{buildroot}%{_sysconfdir}/modprobe.d

%{__install} -d %{buildroot}%{_sysconfdir}/qat/conf_files
%{__install} -m 640 %{qat_src_dir}/build/*.conf %{buildroot}%{_sysconfdir}/qat/conf_files
%{__install} -m 640 %{qat_src_dir}/build/*.vm %{buildroot}%{_sysconfdir}/qat/conf_files

%{__install} -d %{buildroot}%{_sbindir}
%{__install} -m 750 %{qat_src_dir}/build/adf_ctl %{buildroot}%{_sbindir}

%{__install} -d %{buildroot}%{_sysconfdir}/init.d
%{__install} -m 750 %SOURCE2 %{buildroot}%{_sysconfdir}/init.d/qat_service

%{__install} -d %{buildroot}%{_libdir}
%{__install} -m 750 %{qat_src_dir}/build/*.so %{buildroot}%{_libdir}

%{__install} -d %{buildroot}/lib/modules/%{kernel_version}/kernel/drivers/crypto/qat/
%{__install} -m 750 %{qat_src_dir}/build/*qat*.ko %{buildroot}/lib/modules/%{kernel_version}/kernel/drivers/crypto/qat/
%{__install} -m 750 %{qat_src_dir}/build/usdm_drv.ko %{buildroot}/lib/modules/%{kernel_version}/kernel/drivers/crypto/qat

# intel test sample
%{__install} -d %{buildroot}/usr/lib/firmware
%{__install}  -m 750 %{qat_src_dir}/build/cpa_sample_code %{buildroot}%{_sbindir}/cpa_sample_code
%{__install}  -m 640 %{qat_src_dir}/quickassist/lookaside/access_layer/src/sample_code/performance/compression/calgary %{buildroot}/usr/lib/firmware
%{__install}  -m 640 %{qat_src_dir}/quickassist/lookaside/access_layer/src/sample_code/performance/compression/calgary32 %{buildroot}/usr/lib/firmware
%{__install}  -m 640 %{qat_src_dir}/quickassist/lookaside/access_layer/src/sample_code/performance/compression/canterbury %{buildroot}/usr/lib/firmware

# device firmware
# install to the updates directory so this firmware will get grabbed ahead of
# anything supplied by the linux-firmware package
%{__install} -d %{buildroot}/usr/lib/firmware/updates
%{__install}  -m 640 %{qat_src_dir}/build/*.bin %{buildroot}/usr/lib/firmware/updates

# Strip the modules(s).
find %{buildroot} -type f -name \*.ko -exec %{__strip} --strip-debug \{\} \;

# Always Sign the modules(s).
# If the module signing keys are not defined, define them here.
%{!?privkey: %define privkey /usr/src/kernels/%{kernel_version}/signing_key.priv}
%{!?pubkey: %define pubkey /usr/src/kernels/%{kernel_version}/signing_key.x509}
for module in $(find %{buildroot} -type f -name \*.ko);
do %{__perl} /usr/src/kernels/%{kernel_version}/scripts/sign-file \
    sha256 %{privkey} %{pubkey} $module;
done

%clean
%{__rm} -rf %{buildroot}

%files
"%{_sbindir}/*"
"%{_sysconfdir}/default/qat"
"%{_sysconfdir}/init.d/qat_service"
"/lib/modules/%{kernel_version}/kernel/drivers/crypto/qat/*.ko"
"%{_libdir}/*.so"
"/usr/lib/firmware/*"
"/usr/lib/firmware/updates/*"
"%{_sysconfdir}/qat/*"
"%{_sysconfdir}/qat/conf_files/*"
