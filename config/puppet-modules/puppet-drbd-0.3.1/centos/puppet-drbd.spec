%global git_sha     496b3ba9cd74a2d12636f9e90a718739a5451169
%global prefix      puppetlabs
%global module_dir  drbd

Name:           puppet-%{module_dir}
Version:        0.3.1
Release:        rc0%{?_tis_dist}.%{tis_patch_ver}
Summary:        Puppet %{module_dir} module
License:        Apache

URL:            https://github.com/puppetlabs/puppetlabs-drbd

Source0:        %{prefix}-%{module_dir}-%{git_sha}.tar.gz

Patch0001:      0001-TIS-Patches.patch
Patch0002:      0002-Disable-timeout-for-mkfs-command.patch
Patch0003:      0003-drbd-parallel-to-serial-synchronization.patch
Patch0004:      0004-US-96914-reuse-existing-drbd-cinder-resource.patch
Patch0005:      0005-Add-PausedSync-states-to-acceptable-cstate.patch
Patch0006:      0006-CGTS-7164-Add-resource-options-cpu-mask-to-affine-drbd-kernel-threads.patch
Patch0007:      0007-Add-disk-by-path-test.patch
Patch0008:      0008-CGTS-7953-support-for-new-drbd-resources.patch
Patch0009:      0009-drbd-slow-before-swact.patch

BuildArch:      noarch

BuildRequires: python2-devel

# According to .fixtures.yml the following puppet modules are required
Requires:      puppet-concat
Requires:      puppet-stdlib


%description
A Puppet module for configuring drbd

%prep
%setup -n puppetlabs-drbd

find . -type f -name ".*" -exec rm {} +
find . -size 0 -exec rm {} +
find . \( -name "*.pl" -o -name "*.sh"  \) -exec chmod +x {} +
find . \( -name "*.pp" -o -name "*.py"  \) -exec chmod -x {} +
find . \( -name "*.rb" -o -name "*.erb" \) -exec chmod -x {} +
find . \( -name spec -o -name ext \) | xargs rm -rf

%patch0001 -p1
%patch0002 -p1
%patch0003 -p1
%patch0004 -p1
%patch0005 -p1
%patch0006 -p1
%patch0007 -p1
%patch0008 -p1
%patch0009 -p1

%install
rm -rf %{buildroot}
install -d -m 0755 %{buildroot}/%{_datadir}/puppet/modules/%{module_dir}
cp -rp * %{buildroot}/%{_datadir}/puppet/modules/%{module_dir}/

%files
%license %{_datadir}/puppet/modules/%{module_dir}/LICENSE
%{_datadir}/puppet/modules/%{module_dir}

