Summary: centos-release-config
Name: centos-release-config
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown
BuildArch: noarch
Source: %name-%version.tar.gz

Requires: centos-release
Summary: package StarlingX configuration files of centos-release to system folder.

%description
package StarlingX configuration files of centos-release to system folder.

%prep
%setup

%build

%install
# Overwrite default issue files with cgcs related files.
install -d %{buildroot}%{_datadir}/starlingx
install -m 0644 issue %{buildroot}%{_datadir}/starlingx/stx.issue
install -m 0644 issue.net %{buildroot}%{_datadir}/starlingx/stx.issue.net
sed -i -e "s/@PLATFORM_RELEASE@/%{platform_release}/g" \
    %{buildroot}%{_datadir}/starlingx/stx.issue \
    %{buildroot}%{_datadir}/starlingx/stx.issue.net

%post
if [ $1 -eq 1 ] ; then
        # Initial installation
        cp -f %{_datadir}/starlingx/stx.issue %{_sysconfdir}/issue
        cp -f %{_datadir}/starlingx/stx.issue.net %{_sysconfdir}/issue.net
        chmod 644 %{_sysconfdir}/issue
        chmod 644 %{_sysconfdir}/issue.net
fi
%files
%defattr(-,root,root,-)
%{_datadir}/starlingx/stx.issue
%{_datadir}/starlingx/stx.issue.net
