FROM openstackhelm/mariadb:10.2.18

RUN rm /etc/apt/sources.list.d/mariadb.list  && apt-get update && apt-get install -y galera-arbitrator-3

CMD ["/usr/bin/garbd"]

