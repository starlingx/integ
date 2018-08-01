%define _bindir /bin

Summary: ibsh Iron Bar Shell
Name: cgcs-users
Version: 1.0
Release: 0%{?_tis_dist}.%{tis_patch_ver}
License: GPLv2+
Packager: Wind River <info@windriver.com>
Source0: ibsh-0.3e.tar.gz
Source1: admin.cmds
Source2: admin.xtns
Source3: operator.cmds
Source4: operator.xtns
Source5: secadmin.cmds
Source6: secadmin.xtns
Source7: LICENSE
Patch1: ibsh-0.3e.patch
Patch2: ibsh-0.3e-cgcs.patch
Patch3: ibsh-0.3e-cgcs-copyright.patch

%description
CGCS add default users types

%package -n cgcs-users-devel
Summary: ibsh Iron Bar Shell - Development files
Group: devel

%description -n cgcs-users-devel
This package contains symbolic links, header files, and related items
necessary for software development.

%prep
%setup -q

%patch1 -p1
%patch2 -p1
%patch3 -p1

%build
make %{?_smp_mflags} ibsh

%install
rm -rf ${RPM_BUILD_ROOT}
mkdir -p ${RPM_BUILD_ROOT}/%{_sysconfdir}/ibsh/cmds
mkdir -p ${RPM_BUILD_ROOT}/%{_sysconfdir}/ibsh/xtns
cp globals.cmds ${RPM_BUILD_ROOT}/%{_sysconfdir}/ibsh/
cp globals.xtns ${RPM_BUILD_ROOT}/%{_sysconfdir}/ibsh/
cp ${RPM_SOURCE_DIR}/admin.cmds ${RPM_BUILD_ROOT}/%{_sysconfdir}/ibsh/cmds/
cp ${RPM_SOURCE_DIR}/admin.xtns ${RPM_BUILD_ROOT}/%{_sysconfdir}/ibsh/xtns/
cp ${RPM_SOURCE_DIR}/operator.cmds ${RPM_BUILD_ROOT}/%{_sysconfdir}/ibsh/cmds/
cp ${RPM_SOURCE_DIR}/operator.xtns ${RPM_BUILD_ROOT}/%{_sysconfdir}/ibsh/xtns/
cp ${RPM_SOURCE_DIR}/secadmin.cmds ${RPM_BUILD_ROOT}/%{_sysconfdir}/ibsh/cmds/
cp ${RPM_SOURCE_DIR}/secadmin.xtns ${RPM_BUILD_ROOT}/%{_sysconfdir}/ibsh/xtns/
install -d 755 ${RPM_BUILD_ROOT}%{_bindir}
install -m 755 ibsh ${RPM_BUILD_ROOT}%{_bindir}/ibsh

%clean
rm -rf ${RPM_SOURCE_DIR}

%post
chown root ${RPM_BUILD_ROOT}/%{_sysconfdir}/ibsh
chgrp root ${RPM_BUILD_ROOT}/%{_sysconfdir}/ibsh
chown root:root ${RPM_BUILD_ROOT}/%{_sysconfdir}/ibsh/globals.*
chown root:root ${RPM_BUILD_ROOT}/%{_sysconfdir}/ibsh/cmds/admin.cmds
chown root:root ${RPM_BUILD_ROOT}/%{_sysconfdir}/ibsh/cmds/operator.cmds
chown root:root ${RPM_BUILD_ROOT}/%{_sysconfdir}/ibsh/cmds/secadmin.cmds


%files
%defattr(-,root,root,-)
%dir %{_sysconfdir}/ibsh
%dir %{_sysconfdir}/ibsh/cmds
%dir %{_sysconfdir}/ibsh/xtns
%{_sysconfdir}/ibsh/globals.cmds
%{_sysconfdir}/ibsh/globals.xtns
%{_sysconfdir}/ibsh/cmds/secadmin.cmds
%{_sysconfdir}/ibsh/cmds/operator.cmds
%{_sysconfdir}/ibsh/cmds/admin.cmds
%{_sysconfdir}/ibsh/xtns/operator.xtns
%{_sysconfdir}/ibsh/xtns/admin.xtns
%{_sysconfdir}/ibsh/xtns/secadmin.xtns
%{_bindir}/ibsh

%files -n cgcs-users-devel
%defattr(-,root,root,-)

