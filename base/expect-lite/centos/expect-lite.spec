Summary: expect-lite
Name: expect-lite
Version: 4.9.0
Release: 0%{?_tis_dist}.%{tis_patch_ver}
License: BSD
Group: devel
Packager: Wind River <info@windriver.com>
URL: http://expect-lite.sourceforge.net/
Requires: expect
Source0: %{name}_%{version}.tar.gz

%description
Expect based command line automation tool

%prep
%setup -n %{name}.proj

%install
mkdir -p $RPM_BUILD_ROOT/usr/local/bin
echo $PWD
install -m 755 expect-lite $RPM_BUILD_ROOT/usr/local/bin/expect-lite

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
/usr/local/bin/expect-lite
