Name: ldapscripts
Version: 2.0.8
Release: 0%{?_tis_dist}.%{tis_patch_ver}
Summary: ldapscripts

Group: base
License: GPLv2
URL: unknown
Source0: %{name}-%{version}.tgz
Source1: ldapscripts.conf.cgcs
Source2: ldapadduser.template.cgcs
Source3: ldapaddgroup.template.cgcs
Source4: ldapmoduser.template.cgcs
Source5: ldapaddsudo.template.cgcs
Source6: ldapmodsudo.template.cgcs
Source7: ldapscripts.passwd

Patch0: sudo-support.patch
Patch1: sudo-delete-support.patch
Patch2: log_timestamp.patch
Patch3: ldap-user-setup-support.patch
Patch4: allow-anonymous-bind-for-ldap-search.patch

%define debug_package %{nil}

# BuildRequires:	
# Requires:	

%description
Shell scripts that allow to manage POSIX accounts (users, groups, machines) in an LDAP directory.

%prep
%setup -q
%patch0 -p1
%patch1 -p1
%patch2 -p1
%patch3 -p1
%patch4 -p1

%build

%install
make install DESTDIR=%{buildroot}

rm -Rf %{buildroot}/usr/local/man
rm -f %{buildroot}/usr/local/sbin/*machine*
rm -f %{buildroot}/usr/local/etc/ldapscripts/ldapaddmachine.template.sample
install -d %{buildroot}/usr/local/etc/
install -m 644 %{SOURCE1} %{buildroot}/usr/local/etc/ldapscripts/ldapscripts.conf
install -m 644 %{SOURCE2} %{buildroot}/usr/local/etc/ldapscripts/ldapadduser.template.cgcs
install -m 644 %{SOURCE3} %{buildroot}/usr/local/etc/ldapscripts/ldapaddgroup.template.cgcs
install -m 644 %{SOURCE4} %{buildroot}/usr/local/etc/ldapscripts/ldapmoduser.template.cgcs
install -m 644 %{SOURCE5} %{buildroot}/usr/local/etc/ldapscripts/ldapaddsudo.template.cgcs
install -m 644 %{SOURCE6} %{buildroot}/usr/local/etc/ldapscripts/ldapmodsudo.template.cgcs
install -m 600 %{SOURCE7} %{buildroot}/usr/local/etc/ldapscripts/ldapscripts.passwd

%files
%defattr(-,root,root,-)
%dir /usr/local/etc/ldapscripts/
%dir /usr/local/lib/ldapscripts/
/usr/local/sbin/*
%config(noreplace) /usr/local/etc/ldapscripts/ldapscripts.passwd
/usr/local/etc/ldapscripts/*
/usr/local/lib/ldapscripts/*


%changelog

