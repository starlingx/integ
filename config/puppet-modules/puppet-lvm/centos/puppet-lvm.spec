%global git_sha     d0283da637ae24550fb4ba109a48ef8d5d8c8b84
%global prefix      puppetlabs
%global module_dir  lvm

Name:           puppet-%{module_dir}
Version:        0.5.0
Release:        0%{?_tis_dist}.%{tis_patch_ver}
Summary:        Puppet %{module_dir} module
License:        Apache

URL:            https://github.com/puppetlabs/puppetlabs-lvm

Source0:        %{prefix}-%{module_dir}-%{git_sha}.tar.gz

Patch0:         0001-puppet-lvm-kilo-quilt-changes.patch
Patch1:         0002-UEFI-pvcreate-fix.patch
Patch2:         0003-US94222-Persistent-Dev-Naming.patch
Patch3:         0004-extendind-nuke_fs_on_resize_failure-functionality.patch
Patch4:         Fix-the-logical-statement-for-nuke_fs_on_resize.patch

BuildArch:      noarch

BuildRequires: python2-devel

# According to .fixtures.yml the following puppet modules are also required
Requires:      puppet-stdlib


%description
A Puppet module for Logical Resource Management (LVM)

%prep
%setup -c %{module_dir}
%patch0  -p1
%patch1  -p1
%patch2  -p1
%patch3  -p1
%patch4  -p1

%install
install -d -m 0755 %{buildroot}/%{_datadir}/puppet/modules/%{module_dir}
cp -R packstack/puppet/modules/%{module_dir} %{buildroot}/%{_datadir}/puppet/modules

%files
%license packstack/puppet/modules/%{module_dir}/LICENSE
%{_datadir}/puppet/modules/%{module_dir}

