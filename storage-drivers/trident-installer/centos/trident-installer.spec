Summary: trident-installer
Name: trident-installer
Version: 20.04.0
Release: 0%{?_tis_dist}.%{tis_patch_ver}
License: GPLv2 and GPLv2+ and LGPLv2+ and Public Domain and BSD
Group: base
Packager: Wind River <info@windriver.com>
URL: https://github.com/NetApp/trident/releases/download/v20.04.0/trident-installer-20.04.0.tar.gz
Source0: %{name}-%{version}.tar.gz

Requires: nfs-utils

%description
Netapp Trident-installer
https://netapp-trident.readthedocs.io/en/stable-v20.04/introduction.html

%define debug_package %{nil}

%prep
%setup -q

%build

%install
mkdir -p %{buildroot}/%{_bindir}
install -m 755 tridentctl %{buildroot}/%{_bindir}/tridentctl

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{_bindir}/tridentctl
