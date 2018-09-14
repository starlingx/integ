Summary: platform-util
Name: platform-util
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

BuildRequires: python-setuptools

%description
Platform utilities

%package -n platform-util-noncontroller
Summary: non controller platform utilities

%description -n platform-util-noncontroller
Platform utilities that don't get packaged on controller hosts

%package -n platform-util-controller
Summary: controller platform utilities

%description -n platform-util-controller
Platform utilities that packaged on controllers or one node system

%define local_dir /usr/local
%define local_bindir %{local_dir}/bin
%define local_sbindir %{local_dir}/sbin
%define pythonroot /usr/lib64/python2.7/site-packages

%prep
%setup

%build
%{__python} setup.py build

%install
%{__python} setup.py install --root=$RPM_BUILD_ROOT \
                             --install-lib=%{pythonroot} \
                             --prefix=/usr \
                             --install-data=/usr/share \
                             --single-version-externally-managed

%global _buildsubdir %{_builddir}/%{name}-%{version}
install -d %{buildroot}%{local_bindir}
install %{_buildsubdir}/scripts/cgcs_tc_setup.sh %{buildroot}%{local_bindir}
install %{_buildsubdir}/scripts/remotelogging_tc_setup.sh %{buildroot}%{local_bindir}
install %{_buildsubdir}/scripts/connectivity_test %{buildroot}%{local_bindir}

install -d %{buildroot}%{local_sbindir}
install -m 700 -P -D %{_buildsubdir}/scripts/patch-restart-mtce %{buildroot}%{local_sbindir}
install -m 700 -p -D %{_buildsubdir}/scripts/patch-restart-processes %{buildroot}%{local_sbindir}
install -m 700 -p -D %{_buildsubdir}/scripts/patch-restart-haproxy %{buildroot}%{local_sbindir}

install -d %{buildroot}/etc/systemd/system
install -m 644 -p -D %{_buildsubdir}/scripts/opt-platform.mount %{buildroot}/etc/systemd/system
install -m 644 -p -D %{_buildsubdir}/scripts/opt-platform.service %{buildroot}/etc/systemd/system
install -m 644 -p -D %{_buildsubdir}/scripts/memcached.service %{buildroot}/etc/systemd/system

# Mask the systemd ctrl-alt-delete.target, to disable reboot on ctrl-alt-del
ln -sf /dev/null %{buildroot}/etc/systemd/system/ctrl-alt-del.target

%clean
rm -rf $RPM_BUILD_ROOT

%post -n platform-util-noncontroller
mkdir -p /opt/platform
systemctl enable opt-platform.service

%files
%license LICENSE
%defattr(-,root,root,-)
/usr/bin/verify-license
%{local_bindir}/cgcs_tc_setup.sh
%{local_bindir}/remotelogging_tc_setup.sh
%{local_bindir}/connectivity_test
%{local_sbindir}/patch-restart-mtce
%{local_sbindir}/patch-restart-processes
%{local_sbindir}/patch-restart-haproxy
/etc/systemd/system/ctrl-alt-del.target
%dir %{pythonroot}/platform_util
%{pythonroot}/platform_util/*
%dir %{pythonroot}/platform_util-%{version}.0-py2.7.egg-info
%{pythonroot}/platform_util-%{version}.0-py2.7.egg-info/*

%files -n platform-util-noncontroller
%defattr(-,root,root,-)
# This is necessary to mask opt-platform.mount, so that the version generated
# from parsing the fstab is not used by systemd.
/etc/systemd/system/opt-platform.mount
/etc/systemd/system/opt-platform.service

%files -n platform-util-controller
%defattr(-,root,root,-)
/etc/systemd/system/memcached.service
