%global git_sha     7deacd5fdc22c0543455878a8d1872f2f5417c1d
%global module_dir  network

Name:           puppet-network
Version:        1.0.2
Release:        0%{?_tis_dist}.%{tis_patch_ver}
Summary:        Puppet Network module
License:        Apache

URL:            https://github.com/voxpupuli/puppet-network

Source0:        %{name}-%{git_sha}.tar.gz

Patch0:         puppet-network-Kilo-quilt-changes.patch
Patch1:         puppet-network-support-ipv6.patch
Patch2:         Don-t-write-absent-to-redhat-route-files-and-test-fo.patch
Patch3:         fix-absent-options.patch
Patch4:         permit-inservice-update-of-static-routes.patch 
Patch5:         ipv6-static-route-support.patch
Patch6:         route-options-support.patch


BuildArch:      noarch

BuildRequires: python2-devel

%description
A Puppet module to manage non volatile network and route configuration

%prep
%setup -c %{module_dir} 
%patch0  -p1
%patch1  -p1
%patch2  -p1
%patch3  -p1
%patch4  -p1
%patch5  -p1
%patch6  -p1



%install
install -d -m 0755 %{buildroot}/%{_datadir}/puppet/modules/%{module_dir}
cp -R packstack/puppet/modules/%{module_dir} %{buildroot}/%{_datadir}/puppet/modules

%files
%license packstack/puppet/modules/%{module_dir}/LICENSE
%{_datadir}/puppet/modules/%{module_dir}

