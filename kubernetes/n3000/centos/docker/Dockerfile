ARG BASE
FROM ${BASE}
RUN yum install -y \
        pciutils which hwloc-libs libuuid-devel \
        sysvinit-tools epel-release opae opae.admin && \
    yum install -y python-pip && \
    yum clean all && \
    rm -rf /var/cache/yum
RUN pip install intelhex
