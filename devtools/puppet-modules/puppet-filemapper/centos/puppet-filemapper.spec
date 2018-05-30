%global git_sha     9b53310278e76827bbe12a36cc6470d77071abb2
%global module_dir  filemapper

Name:           puppet-filemapper
Version:        1.1.3
Release:        0%{?_tis_dist}.%{tis_patch_ver}
Summary:        Puppet FileMapper module
License:        Apache

URL:            https://github.com/voxpupuli/puppet-filemapper

Source0:        %{name}-%{git_sha}.tar.gz

BuildArch:      noarch

BuildRequires: python2-devel

%description
Puppet module to map files to resources and back

%prep
%autosetup -c %{module_dir}

%install
install -d -m 0755 %{buildroot}/%{_datadir}/puppet/modules/%{module_dir}
cp -R packstack/puppet/modules/%{module_dir} %{buildroot}/%{_datadir}/puppet/modules

%files
%license packstack/puppet/modules/%{module_dir}/LICENSE
%{_datadir}/puppet/modules/%{module_dir}

