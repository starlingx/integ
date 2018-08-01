Summary: Wind River Mellanox port-type configuration scripts
Name: mlx4-config
Version: 1.0.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown

Source1: mlx4-configure.sh
Source2: mlx4-config.service
Source3: LICENSE
Source4: mlx4_core_goenabled.sh
Source5: mlx4_core_config.sh

BuildRequires: chkconfig
BuildRequires: systemd-devel

%description
Wind River Mellanox port-type configuration scripts

%install
%{__install} -d %{buildroot}%{_sysconfdir}/init.d
%{__install} -d %{buildroot}%{_unitdir}
%{__install} -d %{buildroot}%{_sysconfdir}/goenabled.d
%{__install} -d %{buildroot}%{_bindir}
%{__install} -m 755 %SOURCE1 %{buildroot}%{_sysconfdir}/init.d/
%{__install} -m 644 %SOURCE2 %{buildroot}%{_unitdir}/
%{__install} -m 555 %SOURCE4 %{buildroot}%{_sysconfdir}/goenabled.d/
%{__install} -m 755 %SOURCE5 %{buildroot}%{_bindir}/

%clean
%{__rm} -rf %{buildroot}

%post
/bin/systemctl enable mlx4-config.service >/dev/null 2>&1

%preun
/bin/systemctl disable mlx4-config.service >/dev/null 2>&1


%files
%license ../SOURCES/LICENSE
%defattr(-,root,root,-)
%{_sysconfdir}/init.d/mlx4-configure.sh
%{_unitdir}/mlx4-config.service
%{_sysconfdir}/goenabled.d/mlx4_core_goenabled.sh
%{_bindir}/mlx4_core_config.sh
