Summary: wrs-ssl version 1.0.0-r2
Name: wrs-ssl
Version: 1.0.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown
BuildRequires: openssl

Source0: LICENSE
Source1: server-csr.conf
Source2: tpmdevice-setup

%description
Wind River Security

%install
rm -rf $RPM_BUILD_ROOT

RPM_BUILD_DIR_PKG="%{name}-%{version}"
mkdir -p $RPM_BUILD_DIR_PKG
CSRCONF="$RPM_BUILD_DIR_PKG/server-csr.conf"
PEMFILE="$RPM_BUILD_DIR_PKG/server-cert.pem"
cp %{SOURCE1} $CSRCONF
# generate a self signed default certificate
/usr/bin/openssl req -new -x509 -sha256 -keyout $PEMFILE -out $PEMFILE -days 365 -nodes -config $CSRCONF
mkdir -p $RPM_BUILD_ROOT/%{_sysconfdir}/ssl/private
install -m 400 $PEMFILE $RPM_BUILD_ROOT/%{_sysconfdir}/ssl/private/server-cert.pem

mkdir -p $RPM_BUILD_ROOT/%{_sbindir}
install -m 700 %{SOURCE2} $RPM_BUILD_ROOT/%{_sbindir}/tpmdevice-setup

mkdir -p $RPM_BUILD_ROOT/%{_defaultdocdir}/%{name}-%{version}
install -m 644 %{SOURCE0} $RPM_BUILD_ROOT/%{_defaultdocdir}/%{name}-%{version}

%files
%defattr(-,root,root,-)
%{_sysconfdir}/*
%{_sbindir}/*
%{_defaultdocdir}/%{name}-%{version}
