#
# Spec file for IBM's TSS for the TPM 2.0
#
%{!?__global_ldflags: %global __global_ldflags -Wl,-z,relro}

Name:		tss2
Version:	930
Release:	1%{?_tis_dist}.%{tis_patch_ver}
Summary:	IBM's TCG Software Stack (TSS) for TPM 2.0 and related utilities

Group:		Applications/System	
License:	BSD
Source0:	%{name}-%{version}.tar.gz

# tss2 does not work on Big Endian arch yet
ExcludeArch:	ppc64 s390x
BuildRequires:	openssl-devel
Requires:	openssl

%description
TSS2 is a user space Trusted Computing Group's Software Stack (TSS) for
TPM 2.0.  It implements the functionality equivalent to the TCG TSS
working group's ESAPI, SAPI, and TCTI layers (and perhaps more) but with
a hopefully far simpler interface.

It comes with about 80 "TPM tools" that can be used for rapid prototyping,
education and debugging. 

%package devel
Summary:	Development libraries and headers for IBM's TSS 2.0
Group:		Development/Libraries
Requires:	%{name}%{?_isa} = %{version}-%{release}

%description devel
Development libraries and headers for IBM's TSS 2.0. You will need this in
order to build TSS 2.0 applications.

%prep
%setup -q -c %{name}-%{version}

%build
# nonstandard variable names are used in place of CFLAGS and LDFLAGS
pushd %{name}-%{version}/utils
CCFLAGS="%{optflags}" \
LNFLAGS="%{__global_ldflags}" \
make %{?_smp_mflags} 
popd

%install
# Prefix for namespacing
BIN_PREFIX=tss2_
mkdir -p %{buildroot}/%{_bindir}
mkdir -p %{buildroot}/%{_libdir}
mkdir -p %{buildroot}/%{_includedir}/%{name}/
pushd %{name}-%{version}/utils
# Pick out executables and copy with namespacing
for f in *; do
	if [[ -x $f && -f $f && ! $f =~ .*\..* ]]; then
		cp -p $f %{buildroot}/%{_bindir}/${BIN_PREFIX}$f
	fi;
done
cp -p *.so %{buildroot}/%{_libdir}
cp -p %{name}/*.h %{buildroot}/%{_includedir}/%{name}/
popd

%post -p /sbin/ldconfig 
%postun -p /sbin/ldconfig

%files
%license %{name}-%{version}/LICENSE
%{_bindir}/tss2*
%{_libdir}/libtss.so*

%files devel
%{_includedir}/%{name}
%{_libdir}/libtss.so
#%doc ibmtss.doc

%changelog
* Thu Feb 16 2017 Kam Nasim <kam.nasim@windriver.com>  - 930-1
- initial RPM for tss v930 tarball (released: 2017-01-27) 
