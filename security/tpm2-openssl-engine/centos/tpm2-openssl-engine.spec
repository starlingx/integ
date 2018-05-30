Name: tpm2-openssl-engine		
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
Summary: TPM 2.0 Openssl Engine
License: openssl
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown

Source0: %{name}-%{version}.tar.gz

BuildRequires: openssl-devel
BuildRequires: openssl
BuildRequires: tss2-devel
Requires: tss2

%description
TPM 2.0 OpenSSL engine. Leveraged by applications
to provide secure TLS Decryption and Signing capabilities

%prep
%setup -q

%build
make %{?_smp_mflags}

%install
make install ENGINEDIR=%{buildroot}/%{_libdir}/openssl/engines UTILDIR=%{buildroot}/usr/sbin


%files
%license LICENSE

%defattr(-,root,root,-)

%{_libdir}/openssl/engines/libtpm2.so
/usr/sbin/create_tpm2_key


