%global git_sha     480f13af6d17d1d3fcf0dc7b4bd04b49fa4099e1
%global module_dir  ldap

Name:           puppet-ldap
Version:        0.2.4
Release:        0%{?_tis_dist}.%{tis_patch_ver}
Summary:        Puppet LDAP module
License:        GPLv2

URL:            https://github.com/torian/puppet-ldap

Source0:        %{name}-%{git_sha}.tar.gz

BuildArch:      noarch

BuildRequires: python2-devel

%description
A Puppet module to manage client and server configuration for OpenLdap

%prep
%setup -n puppet-ldap-master

%install
install -d -m 0755 %{buildroot}/%{_datadir}/puppet/modules/%{module_dir}
cp -R ../puppet-ldap-master/* %{buildroot}/%{_datadir}/puppet/modules/%{module_dir}/.

%files
%{_datadir}/puppet/modules/%{module_dir}

