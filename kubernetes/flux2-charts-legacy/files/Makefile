# Copyright (c) 2025 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# It's necessary to set this because some environments don't link sh -> bash.
SHELL := /bin/bash

all: build clean

lint:
	helm lint flux2/

build: lint
	helm package flux2

clean:
	@echo "Clean all build artifacts"
	rm -f flux2/templates/_partials.tpl flux2/templates/_globals.tpl
	rm -rf flux2/charts
