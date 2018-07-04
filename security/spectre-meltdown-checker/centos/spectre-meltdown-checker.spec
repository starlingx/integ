Name: spectre-meltdown-checker
Version: 0.37+
Release: %{tis_patch_ver}%{?_tis_dist}
Summary: Checker script for spectre/meltdown

Group: base
License: GPLv3
URL: https://github.com/speed47/spectre-meltdown-checker.git
Source0: spectre-meltdown-checker-0.37+-5cc77741.tar.gz

BuildArch: noarch
Requires: bash

%description
Script to check whether kernel is susceptible to spectre/meltdown vulnerabilities.


%prep
tar xf %{SOURCE0}

%build


%install
install -d -m 755 %{buildroot}/usr/sbin/
install -m 744 spectre-meltdown-checker/spectre-meltdown-checker.sh %{buildroot}/usr/sbin/spectre-meltdown-checker.sh


%files
%license %{name}/LICENSE
/usr/sbin/*


%changelog

