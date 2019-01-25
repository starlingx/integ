Summary: Titanuim Server collectd Package
Name: collectd-extensions
Version: 1.0
Release: 0%{?_tis_dist}.%{tis_patch_ver}
License: windriver
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown

# create the files tarball
Source0: %{name}-%{version}.tar.gz
Source1: collectd.service
Source2: collectd.conf.pmon

# collectd python plugin files - notifiers
Source3: fm_notifier.py
Source4: mtce_notifier.py
Source5: plugin_common.py

# collectd python plugin files - resource plugins
Source11: cpu.py
Source12: memory.py
Source14: example.py
Source15: ntpq.py
Source16: interface.py

# collectd plugin conf files into /etc/collectd.d
Source100: python_plugins.conf
Source101: cpu.conf
Source102: memory.conf
Source103: df.conf
Source104: example.conf
Source105: ntpq.conf
Source106: interface.conf

BuildRequires: systemd-devel

Requires: systemd
Requires: collectd
Requires: /bin/systemctl

%description
Titanium Cloud collectd extensions

%define debug_package %{nil}
%define local_unit_dir %{_sysconfdir}/systemd/system
%define local_plugin_dir %{_sysconfdir}/collectd.d
%define local_python_extensions_dir /opt/collectd/extensions/python
%define local_config_extensions_dir /opt/collectd/extensions/config

%prep
%setup

%build

%install
install -m 755 -d %{buildroot}%{_sysconfdir}
install -m 755 -d %{buildroot}%{local_unit_dir}
install -m 755 -d %{buildroot}%{local_plugin_dir}
install -m 755 -d %{buildroot}%{local_config_extensions_dir}
install -m 755 -d %{buildroot}%{local_python_extensions_dir}

# support files ; service and pmon conf
install -m 644 %{SOURCE1} %{buildroot}%{local_unit_dir}
install -m 600 %{SOURCE2} %{buildroot}%{local_config_extensions_dir}

# collectd python plugin files - notifiers
install -m 700 %{SOURCE3} %{buildroot}%{local_python_extensions_dir}
install -m 700 %{SOURCE4} %{buildroot}%{local_python_extensions_dir}
install -m 700 %{SOURCE5} %{buildroot}%{local_python_extensions_dir}

# collectd python plugin files - resource plugins
install -m 700 %{SOURCE11} %{buildroot}%{local_python_extensions_dir}
install -m 700 %{SOURCE12} %{buildroot}%{local_python_extensions_dir}
install -m 700 %{SOURCE14} %{buildroot}%{local_python_extensions_dir}
install -m 700 %{SOURCE15} %{buildroot}%{local_python_extensions_dir}
install -m 700 %{SOURCE16} %{buildroot}%{local_python_extensions_dir}


# collectd plugin conf files into /etc/collectd.d
install -m 600 %{SOURCE100} %{buildroot}%{local_plugin_dir}
install -m 600 %{SOURCE101} %{buildroot}%{local_plugin_dir}
install -m 600 %{SOURCE102} %{buildroot}%{local_plugin_dir}
install -m 600 %{SOURCE103} %{buildroot}%{local_plugin_dir}
install -m 600 %{SOURCE104} %{buildroot}%{local_plugin_dir}
install -m 600 %{SOURCE105} %{buildroot}%{local_plugin_dir}
install -m 600 %{SOURCE106} %{buildroot}%{local_plugin_dir}

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%config(noreplace) %{local_unit_dir}/collectd.service
%{local_plugin_dir}/*
%{local_config_extensions_dir}/*
%{local_python_extensions_dir}/*
