Name: k8s-pod-recovery
Version: 1.0
Release: 0%{?_tis_dist}.%{tis_patch_ver}
Summary: Kubernetes Pod Recovery Service
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown
Source0: k8s-pod-recovery
Source1: k8s-pod-recovery.service

Requires: /bin/bash
Requires: systemd

%description
%{summary}

%define local_dir /usr/local
%define local_sbindir %{local_dir}/sbin

%prep

%install
install -d %{buildroot}%{local_sbindir}
install -m 755 %{SOURCE0} %{buildroot}%{local_sbindir}/k8s-pod-recovery
install -p -D -m 644 %{SOURCE1} %{buildroot}%{_unitdir}/k8s-pod-recovery.service

%post
if [ $1 -eq 1 ]; then
    # Package install: enable and start it
    /usr/bin/systemctl enable k8s-pod-recovery.service > /dev/null 2>&1 || :
    /usr/bin/systemctl start k8s-pod-recovery.service > /dev/null 2>&1 || :
else
    # Package upgrade: reenable in case [Install] changes and restart to pick up
    # new actions
    if /usr/bin/systemctl --quiet is-enabled k8s-pod-recovery.service ; then
        /usr/bin/systemctl reenable k8s-pod-recovery.service > /dev/null 2>&1 || :
        /usr/bin/systemctl restart k8s-pod-recovery.service > /dev/null 2>&1 || :
    fi
fi

%preun
if [ $1 -eq 0 ]; then
    /usr/bin/systemctl stop k8s-pod-recovery.service > /dev/null 2>&1 || :
    /usr/bin/systemctl disable k8s-pod-recovery.service > /dev/null 2>&1 || :
fi


%files
%defattr(-,root,root,-)
%{local_sbindir}/k8s-pod-recovery
%{_unitdir}/k8s-pod-recovery.service
