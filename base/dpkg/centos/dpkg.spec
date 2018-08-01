Summary: dpkg
Name: dpkg
Version: 1.18.24
Release: 0%{?_tis_dist}.%{tis_patch_ver}
License: GPLv2 and GPLv2+ and LGPLv2+ and Public Domain and BSD
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown
Source0: %{name}_%{version}.tar.xz

BuildRequires: gcc
BuildRequires: gcc-c++
BuildRequires: ncurses-static
BuildRequires: perl-version

%description
dpkg

%define local_bindir /usr/bin/

%prep
%setup

%build
./configure --prefix=$RPM_BUILD_ROOT \
            --disable-dselect \
            --disable-update-alternatives \
            --without-liblzma
make -j"%(nproc)"

%install
# Don't install everything, it's too dangerous
# make install

install -d -m 755 %{buildroot}%{local_bindir}
install -p -D -m 700 utils/start-stop-daemon %{buildroot}%{local_bindir}/start-stop-daemon

%clean
rm -rf $RPM_BUILD_ROOT 

%files
%defattr(-,root,root,-)
%{local_bindir}/*
