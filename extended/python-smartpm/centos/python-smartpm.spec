Summary:    The Smart Package Manager
Name:       python-smartpm
Version:    1.4.1
Release:    0%{?_tis_dist}.%{tis_patch_ver}
License:    GPLv2
Group:      devel/python
Packager:   Wind River <info@windriver.com>
URL:        http://labix.org/smart/

Source0:     %{name}-%{version}.tar.gz

#OVP Patches
#Patch00:    smartpm-rpm5-nodig.patch
Patch01:    smart-rpm-root.patch
Patch02:    smart-recommends.patch
Patch03:    smart-rpm-extra-macros.patch
Patch04:    smart-dflags.patch
Patch05:    smart-rpm-md-parse.patch
Patch06:    smart-tmpdir.patch
Patch07:    smart-metadata-match.patch
Patch08:    smart-improve-error-reporting.patch
Patch09:    smart-multilib-fixes.patch
Patch10:    smart-yaml-error.patch
Patch11:    smart-channelsdir.patch
Patch12:    smart-conflict-provider.patch
Patch13:    smart-flag-ignore-recommends.patch
Patch14:    smart-flag-exclude-packages.patch
Patch15:    smart-config-ignore-all-recommends.patch
Patch16:    smart-attempt.patch
Patch17:    smart-filename-NAME_MAX.patch
Patch18:    smart-add-for-rpm-ignoresize-check.patch
Patch19:    smart-set-noprogress-for-pycurl.patch

#WRS Patches
Patch20:    commit_transaction_error_handling.patch
Patch21:    smart-support-rpm4.patch

BuildArch:  x86_64

BuildRequires: python
BuildRequires: python-devel
BuildRequires: gettext
BuildRequires: rpm

Requires: python
Requires: python-devel
# Note: centos has RPM 4.11.3   WR was using 5.4.9
Requires: rpm
Requires: rpm-python

%description
The Smart Package Manager project has the ambitious objective of creating
smart and portable algorithms for solving adequately the problem of
managing software upgrades and installation.

%prep
%autosetup -p 1 -n smart-%{version}

# Remove bundled egg-info
rm -rf %{name}.egg-info

%build
%{__python2} setup.py build

%install
%{__python2} setup.py install --skip-build --root %{buildroot}

# WRS Note:
# python2_sitelib  is not correct for this package.
# This SPEC looks under /usr/lib but needs to look under /usr/lib64
# The files section is hardcoded to handle this

%files
%license LICENSE
%{_bindir}/smart
#%{python2_sitelib}/smart
/usr/lib64/python2.7/site-packages/smart
#%{python2_sitelib}/*.egg-info
/usr/lib64/python2.7/site-packages/*.egg-info
/usr/share/locale
/usr/share/man

