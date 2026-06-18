FROM quay.io/airshipit/mariadb:ubuntu_noble-20260511

RUN echo "deb http://archive.mariadb.org/mariadb-11.4.8/repo/ubuntu/ noble main" > /etc/apt/sources.list.d/mariadb.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends galera-arbitrator-4 && \
    rm -f /etc/apt/sources.list.d/mariadb.list && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

CMD ["/usr/bin/garbd"]

