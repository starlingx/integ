# increment this every release
API_VERSION := "1.9.0"

build:
	@git status > /dev/null ; \
	if [ $$? -ne 0 ] ; then \
		echo CREATING DUMMY GIT ; \
        git init ; \
	fi

	if [ ! -e mvn.repo.tgz ]; then	\
		echo "Maven Cache Not Found!"	;	\
		exit 1	;	\
	fi

	mkdir -p mvn.repo
	tar -xvzf ./mvn.repo.tgz -C ./mvn.repo/
	mvn clean generate-sources -o -Dmaven.repo.local=./mvn.repo/

	mkdir -p target/wrs-restapi-doc-$(API_VERSION)/
	cp rest-api-usage-example.pdf target/wrs-restapi-doc-$(API_VERSION)/
	cp -R api-ref-guides/target/docbkx/pdf target/wrs-restapi-doc-$(API_VERSION)/
	cp -R api-ref/target/docbkx/html target/wrs-restapi-doc-$(API_VERSION)/
	cd target; tar -czvf ../wrs-restapi-doc-$(API_VERSION).tgz wrs-restapi-doc-$(API_VERSION)
	@echo 'wrs-restapi-doc-$(API_VERSION).tgz' is ready

clean:
	mvn clean -o -Dmaven.repo.local=./mvn.repo/
	rm -f wrs-restapi-doc-*.tgz
	rm -rf target
	
	rm -rf mvn.repo
