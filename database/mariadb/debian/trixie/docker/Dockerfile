FROM quay.io/airshipit/mariadb:ubuntu_noble-20260511

RUN rm /etc/apt/sources.list.d/mariadb.list  && apt-get update && apt-get install -y galera-arbitrator-4

CMD ["/usr/bin/garbd"]

