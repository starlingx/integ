#
# Copyright (c) 2023 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

VER=1
VER_MJR=1

build:
	(cd encryption ; make all VER=$(VER) VER_MJR=$(VER_MJR))

clean:
	@( cd encryption ; make clean )


backup: clean
	mkdir -p ~/luks
	cp -a * ~/luks
