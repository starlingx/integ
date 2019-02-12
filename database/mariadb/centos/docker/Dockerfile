FROM openstackhelm/mariadb:10.2.18

RUN apt-get update && apt-get install -y galera-arbitrator-3

CMD ["/usr/bin/garbd"]

