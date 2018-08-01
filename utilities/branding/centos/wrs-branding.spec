Summary: Titanium Cloud Branding Information
Name: wrs-branding
Version: 4.0.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown

Source0: %{name}-%{version}.tar.gz

%define cgcs_sdk_deploy_dir /opt/deploy/cgcs_sdk

%description
Titanium Cloud Branding allows alternate branding to be used for Horizon
in place of the default included with Titanium Cloud.

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/%{cgcs_sdk_deploy_dir}
install -m 644 %{SOURCE0} $RPM_BUILD_ROOT/%{cgcs_sdk_deploy_dir}/%{name}-%{version}.tgz

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%{cgcs_sdk_deploy_dir}
