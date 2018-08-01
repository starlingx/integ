%global git_sha     b8c19b1ada89865f2e50758e054583798ad8011a
%global module_dir  nslcd

Name:           puppet-nslcd
Version:        0.0.1
Release:        0%{?_tis_dist}.%{tis_patch_ver}
Summary:        Puppet nslcd module
License:        Apache

URL:            https://github.com/jlyheden/puppet-nslcd

Source0:        %{name}-%{git_sha}.tar.gz

BuildArch:      noarch

BuildRequires: python2-devel

%description
A Puppet module for nslcd - local LDAP name service daemon

%prep
%autosetup -c %{module_dir}

%install
install -d -m 0755 %{buildroot}/%{_datadir}/puppet/modules/%{module_dir}
cp -R packstack/puppet/modules/%{module_dir} %{buildroot}/%{_datadir}/puppet/modules

%files
#%license packstack/puppet/modules/%{module_dir}/LICENSE
%{_datadir}/puppet/modules/%{module_dir}

