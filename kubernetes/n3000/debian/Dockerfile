FROM centos:7.9.2009
RUN yum install -y \
        pciutils which hwloc-libs libuuid-devel \
        sysvinit-tools epel-release \
        http://mirror.starlingx.cengn.ca/mirror/centos/github.com/OPAE/opae-sdk/releases/download/1.3.7-5/opae-devel-1.3.7-5.el7.x86_64.rpm \
        http://mirror.starlingx.cengn.ca/mirror/centos/github.com/OPAE/opae-sdk/releases/download/1.3.7-5/opae-libs-1.3.7-5.el7.x86_64.rpm \
        http://mirror.starlingx.cengn.ca/mirror/centos/github.com/OPAE/opae-sdk/releases/download/1.3.7-5/opae-tools-1.3.7-5.el7.x86_64.rpm \
        http://mirror.starlingx.cengn.ca/mirror/centos/github.com/OPAE/opae-sdk/releases/download/1.3.7-5/opae-tools-extra-1.3.7-5.el7.x86_64.rpm \
        http://mirror.starlingx.cengn.ca/mirror/centos/github.com/OPAE/opae-sdk/releases/download/1.3.7-5/opae.admin-1.0.3-2.el7.noarch.rpm && \
    yum install -y python-pip && \
    yum clean all && \
    rm -rf /var/cache/yum
RUN pip install intelhex
