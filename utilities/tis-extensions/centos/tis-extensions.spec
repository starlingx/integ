#
# The tis-extensions group of packages is intended to allow us to
# add files to "extend" thirdparty packages, such as by packaging
# custom systemd files into /etc/systemd to override the originals
# without modifying or rebuilding the thirdparty package.
#

Name: tis-extensions
Version: 1.0
Summary: TIS Extensions to thirdparty pkgs
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown
Source0: %{name}-%{version}.tar.gz

%define debug_package %{nil}

Requires: systemd

%description
TIS Extensions to thirdparty pkgs

%package -n %{name}-controller
Summary: TIS Extensions to thirdparty pkg on controller
Group: base

%description -n %{name}-controller
TIS Extensions to thirdparty pkgs on controller

%define local_etc_systemd %{_sysconfdir}/systemd/system/
%define local_etc_coredump %{_sysconfdir}/systemd/coredump.conf.d
%define local_etc_initd %{_sysconfdir}/init.d
%define local_etc_sysctl %{_sysconfdir}/sysctl.d
%define local_etc_modload %{_sysconfdir}/modules-load.d

%prep
%setup

%build

%install
install -d -m 755 %{buildroot}%{local_etc_initd}
install -p -D -m 555 target %{buildroot}%{local_etc_initd}/target

install -d -m 755 %{buildroot}%{local_etc_systemd}
install -p -D -m 444 target.service %{buildroot}%{local_etc_systemd}/target.service

install -d -m 755 %{buildroot}%{local_etc_sysctl}
install -p -D -m 644 coredump-sysctl.conf %{buildroot}%{local_etc_sysctl}/50-coredump.conf

install -d -m 755 %{buildroot}%{local_etc_coredump}
install -p -D -m 644 coredump.conf %{buildroot}%{local_etc_coredump}/coredump.conf

install -d -m 755 %{buildroot}%{local_etc_modload}
install -p -D -m 644 modules-load-vfio.conf %{buildroot}%{local_etc_modload}/vfio.conf

%files
%defattr(-,root,root,-)
%{local_etc_sysctl}/50-coredump.conf
%{local_etc_coredump}/coredump.conf
%{local_etc_modload}/vfio.conf
%doc LICENSE

%files -n %{name}-controller
%defattr(-,root,root,-)
%{local_etc_initd}/target
%{local_etc_systemd}/target.service
