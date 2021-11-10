%global git_sha     3f80054a342cccb5d368be4cea64c67e09a8d4d6
%global prefix      puppetlabs
%global module_dir  postgresql

Name:           puppet-%{module_dir}
Version:        6.7.0
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

