%global git_sha     22b726dd78b0a60a224cc7054aebbf28e9306f62
%global module_dir  boolean 

Name:           puppet-boolean
Version:        1.0.2
Release:        1%{?_tis_dist}.%{tis_patch_ver}
Summary:        Puppet Boolean module
License:        Apache

URL:            https://github.com/adrienthebo/puppet-boolean

Source0:        %{name}-%{git_sha}.tar.gz

BuildArch:      noarch

BuildRequires: python2-devel

%description
A Puppet module to provide boolean parameters

%prep
%setup -n %{name}

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

