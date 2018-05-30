%global git_sha     4639819a7f3a4fa9310d2ba583c63e467df7e2c3
%global prefix      puppetlabs
%global module_dir  create_resources

Name:           puppet-%{module_dir}
Version:        0.0.1
Release:        0%{?_tis_dist}.%{tis_patch_ver}
Summary:        Puppet %{module_dir} module
License:        Apache

URL:            https://github.com/puppetlabs/puppetlabs-create_resources

Source0:        %{prefix}-%{module_dir}-%{git_sha}.tar.gz

BuildArch:      noarch

BuildRequires: python2-devel

%description
A Puppet module to dynamically add resources to the catalog

%prep
%autosetup -c %{module_dir}

%install
install -d -m 0755 %{buildroot}/%{_datadir}/puppet/modules/%{module_dir}
cp -R packstack/puppet/modules/%{module_dir} %{buildroot}/%{_datadir}/puppet/modules

%files
%license packstack/puppet/modules/%{module_dir}/LICENSE
%{_datadir}/puppet/modules/%{module_dir}

