#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

install:
	install -d -m 0755 $(SYSCONFDIR)/pmon.d
	install -D -m 644 docker-pmond.conf $(SYSCONFDIR)/pmon.d/docker.conf
	install -d -m 0755 $(SYSCONFDIR)/systemd/system/docker.service.d
	install -D -m 644 docker-stx-override.conf $(SYSCONFDIR)/systemd/system/docker.service.d/docker-stx-override.conf
