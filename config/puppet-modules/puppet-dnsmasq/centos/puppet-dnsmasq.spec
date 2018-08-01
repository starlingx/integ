%global git_sha     cff07e90890662972c97684a2baee964f68ff3ed
%global module_dir  dnsmasq

Name:           puppet-dnsmasq
Version:        1.1.0
Release:        0%{?_tis_dist}.%{tis_patch_ver}
Summary:        Puppet dnsmasq module
License:        Apache

URL:            github.com/netmanagers/puppet-dnsmasq

Source0:        %{name}-%{git_sha}.tar.gz

Patch0:         0001-puppet-dnsmasq-Kilo-quilt-patches.patch
Patch1:         0002-Fixing-mismatched-permission-on-dnsmasq-conf.patch
Patch2:         0003-Support-management-of-tftp_max-option.patch
Patch3:         0004-Enable-clear-DNS-cache-on-reload.patch

BuildArch:      noarch

BuildRequires: python2-devel

Requires:      puppet-concat
Requires:      puppet-puppi

%description
A Puppet module for dnsmasq

%prep
%setup -c %{module_dir}
%patch0  -p1
%patch1  -p1
%patch2  -p1
%patch3  -p1

%install
install -d -m 0755 %{buildroot}/%{_datadir}/puppet/modules/%{module_dir}
cp -R packstack/puppet/modules/%{module_dir} %{buildroot}/%{_datadir}/puppet/modules

%files
#%license packstack/puppet/modules/%{module_dir}/LICENSE
%{_datadir}/puppet/modules/%{module_dir}

