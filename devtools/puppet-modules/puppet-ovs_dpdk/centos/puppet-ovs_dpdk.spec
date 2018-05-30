%global module_dir  ovs_dpdk

Name:           puppet-%{module_dir}
Version:        1.0.0
Release:        %{tis_patch_ver}%{?_tis_dist}
Summary:        Puppet ovs_dpdk module
License:        Apache

URL:            unknown

Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires: python2-devel

%description
A puppet module for ovs dpdk

%prep
%autosetup -c %{module_dir}

#
# The src for this puppet module needs to be staged to puppet/modules
#
%install
install -d -m 0755 %{buildroot}%{_datadir}/puppet/modules/%{module_dir}
cp -R %{name}-%{version}/%{module_dir} %{buildroot}%{_datadir}/puppet/modules

%files
%{_datadir}/puppet/modules/%{module_dir}

