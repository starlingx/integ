%global git_sha     c1c47f4edfd761d1bbde32a75da0c3fa7cc93a81
%global module_dir  puppi

Name:           puppet-puppi
Version:        2.2.3
Release:        0%{?_tis_dist}.%{tis_patch_ver}
Summary:        Puppet Puppi module
License:        Apache

URL:            https://github.com/example42/puppi

Source0:        %{module_dir}-%{git_sha}.tar.gz

BuildArch:      noarch

BuildRequires: python2-devel

%description
A Puppet module to provide puppet knowledge to CLI

%prep
%setup -n puppi-master

%install
install -d -m 0755 %{buildroot}/%{_datadir}/puppet/modules/%{module_dir}
cp -R ../puppi-master/* %{buildroot}/%{_datadir}/puppet/modules/%{module_dir}/.

%files
%license %{_datadir}/puppet/modules/%{module_dir}/LICENSE
%{_datadir}/puppet/modules/%{module_dir}

