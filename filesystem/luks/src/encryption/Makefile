#
# Copyright (c) 2023 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

SHELL = /bin/bash

CFLAGS = -Wall -Wextra -g -Werror -std=c++11
LIBS = -lstdc++ -lstdc++ -ljson-c
INCLUDES = -I.

CC=g++

SRC = luks-fs-mgr.cpp
EXECUTABLE = luks-fs-mgr

.PHONY: all clean

all: $(EXECUTABLE)

$(EXECUTABLE): $(SRC)
	$(CC) $(CFLAGS) -o $@ $< $(LIBS)

clean:
	rm -f $(EXECUTABLE) *.o
