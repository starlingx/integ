%global git_sha     d022a56b28b2174456fc0f6adc51a4b54493afad
%global prefix      puppetlabs
%global module_dir  postgresql

Name:           puppet-%{module_dir}
Version:        4.8.0
Release:        0%{?_tis_dist}.%{tis_patch_ver}
Summary:        Puppet %{module_dir} module
License:        Apache

URL:            https://github.com/puppetlabs/puppetlabs-postgresql

Source0:        %{prefix}-%{module_dir}-%{git_sha}.tar.gz

Patch0001:      0001-Roll-up-TIS-patches.patch
Patch0002:      0002-remove-puppetlabs-apt-as-a-requirement.patch

BuildArch:      noarch

BuildRequires: python2-devel

# According to .fixtures.yml the following puppet modules are also needed
#Requires:      puppet-apt
Requires:      puppet-stdlib
Requires:      puppet-firewall
Requires:      puppet-concat


%description
A Puppet module for managing PostgreSQL databases

%prep
%setup -n %{prefix}-%{module_dir}
%patch0001  -p1
%patch0002  -p1

find . -type f -name ".*" -exec rm {} +
find . -size 0 -exec rm {} +
find . \( -name "*.pl" -o -name "*.sh"  \) -exec chmod +x {} +
find . \( -name "*.pp" -o -name "*.py"  \) -exec chmod -x {} +
find . \( -name "*.rb" -o -name "*.erb" \) -exec chmod -x {} +
find . \( -name spec -o -name ext \) | xargs rm -rf

%install
rm -rf %{buildroot}
install -d -m 0755 %{buildroot}/%{_datadir}/puppet/modules/%{module_dir}
cp -rp * %{buildroot}/%{_datadir}/puppet/modules/%{module_dir}/

%files
%license %{_datadir}/puppet/modules/%{module_dir}/LICENSE
%{_datadir}/puppet/modules/%{module_dir}

