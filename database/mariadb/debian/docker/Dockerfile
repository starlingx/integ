FROM openstackhelm/mariadb:ubuntu_focal-20250111

RUN rm /etc/apt/sources.list.d/mariadb.list  && apt-get update && apt-get install -y galera-arbitrator-4

CMD ["/usr/bin/garbd"]

