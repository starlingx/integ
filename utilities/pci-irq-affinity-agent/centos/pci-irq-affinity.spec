Summary: StarlingX PCI Interrupt Affinity Agent Package
Name: pci-irq-affinity-agent
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: StarlingX
URL: unknown

Source0: %{name}-%{version}.tar.gz

Requires:   python-novaclient
BuildRequires: python-setuptools
BuildRequires: systemd-devel

%description
StarlingX PCI Interrupt Affinity Agent Package

%define local_etc_initd /etc/init.d/
%define local_etc_pmond /etc/pmon.d/
%define pythonroot           /usr/lib64/python2.7/site-packages
%define debug_package %{nil}

%prep
%setup

# Remove bundled egg-info
rm -rf *.egg-info

%build
%{__python} setup.py build

%install
%{__python} setup.py install --root=%{buildroot} \
                             --install-lib=%{pythonroot} \
                             --prefix=/usr \
                             --install-data=/usr/share \
                             --single-version-externally-managed

%{__install}  -d -m 755 %{buildroot}%{local_etc_initd}
%{__install}  -p -D -m 755 pci-irq-affinity-agent %{buildroot}%{local_etc_initd}/pci-irq-affinity-agent

%{__install}  -d -m 755 %{buildroot}%{local_etc_pmond}
%{__install}  -p -D -m 644 pci-irq-affinity-agent.conf %{buildroot}%{local_etc_pmond}/pci-irq-affinity-agent.conf
%{__install}  -p -D -m 644 pci-irq-affinity-agent.service %{buildroot}%{_unitdir}/pci-irq-affinity-agent.service

%{__install}  -d  %{buildroot}%{_bindir}
%{__install}  -p -D -m 755 nova-sriov %{buildroot}%{_bindir}/nova-sriov

%{__install}  -d  %{buildroot}%{_sysconfdir}/pci_irq_affinity
%{__install}  -p -D -m 600 config.ini %{buildroot}%{_sysconfdir}/pci_irq_affinity/config.ini

%post
/usr/bin/systemctl enable pci-irq-affinity-agent.service >/dev/null 2>&1

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc LICENSE
%{local_etc_initd}/pci-irq-affinity-agent
%{local_etc_pmond}/pci-irq-affinity-agent.conf
%{_unitdir}/pci-irq-affinity-agent.service
%{pythonroot}/pci_irq_affinity/*
%{pythonroot}/pci_irq_affinity_agent-%{version}*.egg-info

%{_bindir}/pci-irq-affinity-agent
%{_bindir}/nova-sriov
%config(noreplace) %{_sysconfdir}/pci_irq_affinity/config.ini
