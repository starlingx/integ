%global git_sha     b1dbff4b0bd1e1f40d237e21011f6dee0ec2fa69

Summary: inih
Name: inih
Version: 44
Release: 0%{?_tis_dist}.%{tis_patch_ver}
License: New BSD
Group: base
Packager: Wind River <info@windriver.com>
URL: https://github.com/benhoyt/inih/releases/tag/r44
Source0: %{name}-%{git_sha}.tar.gz

BuildRequires: gcc
BuildRequires: gcc-c++
BuildRequires: ncurses-static
BuildRequires: perl-version

%define debug_package %{nil}
%description
Simple .INI file parser written in C

%prep
%setup

%build
pushd extra > /dev/null
make -f Makefile.static
popd > /dev/null

%install
install -d -m 755 %{buildroot}%{_libdir}
install -d -m 755 %{buildroot}%{_includedir}
install -d -m 755 %{buildroot}%{_datadir}/inih/
install -p -D -m 755 extra/libinih.a %{buildroot}%{_libdir}/libinih.a
install -p -D -m 644 ini.h %{buildroot}%{_includedir}/ini.h
install -p -D -m 644 LICENSE.txt %{buildroot}%{_datadir}/inih/LICENSE.txt

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%{_libdir}/*
%{_includedir}/*
%{_datadir}/*
